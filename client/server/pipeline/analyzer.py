"""
server/pipeline/analyzer.py

Turns raw book text into the instruction payload the device replays:

    [{"w": "word", "i": <wpm to subtract>, "p": <extra pause in ms>}, ...]

Three layers of signal, cheapest first:

1. Lexical   - word length, part of speech, numbers, proper nouns.
2. Structural- sentence length and clause density, punctuation, paragraphs.
3. Rarity    - how unusual a word is *for this book*. A local stand-in for
               surprisal: a word that shows up twice in 90k words is a
               word the reader has to stop and think about.
4. Optional LLM pass - flags genuinely hard passages and plot turns that
               the statistics above cannot see.

Nothing here raises at import time. If spaCy or the model is missing the
pipeline falls back to a regex tokenizer so the server still runs.
"""

import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

# --------------------------------------------------------------------- spaCy

_NLP = None
_NLP_STATUS = "not loaded"


def _load_nlp():
    """Loaded lazily so importing this module never blows up the server."""
    global _NLP, _NLP_STATUS
    if _NLP is not None:
        return _NLP
    try:
        import spacy
        # Parser is the slow component and we only need sentence bounds,
        # so swap it for the rule-based sentencizer. ~10x faster on books.
        nlp = spacy.load("en_core_web_sm",
                         exclude=["ner", "lemmatizer", "parser"])
        nlp.add_pipe("sentencizer")
        nlp.max_length = 3_000_000
        _NLP = nlp
        _NLP_STATUS = "spacy:en_core_web_sm"
    except Exception as exc:
        _NLP = False
        _NLP_STATUS = f"fallback (spaCy unavailable: {exc})"
    return _NLP


def nlp_status() -> str:
    _load_nlp()
    return _NLP_STATUS


# ------------------------------------------------------------------- tuning

@dataclass
class PenaltyConfig:
    """Every number is "WPM to subtract". Tune these and re-analyze."""
    word_len_medium: int = 15     # 8-10 characters
    word_len_long: int = 35       # 11+ characters
    proper_noun: int = 25
    number: int = 30
    rare_in_book: int = 45        # appears very few times in this book
    uncommon_in_book: int = 20
    sentence_long: int = 20       # 25+ tokens
    sentence_very_long: int = 35  # 40+ tokens
    clause_dense: int = 15        # many commas / conjunctions
    sentence_first_word: int = 10  # re-orienting at a new sentence
    dialogue_open: int = 15
    llm_hard_word: int = 60
    llm_slow_sentence: int = 40
    max_penalty: int = 220        # never subtract more than this

    # Pauses in ms, added on top of the per-word delay
    pause_comma: int = 60
    pause_sentence: int = 180
    pause_paragraph: int = 320


SENTENCE_END = {".", "!", "?", "...", "\u2026"}
CLAUSE_MARK = {",", ";", ":", "-", "--"}
CONJUNCTIONS = {"which", "although", "however", "whereas", "despite",
                "nevertheless", "therefore", "unless", "whilst", "moreover"}

# Function words are never "rare" no matter how few times they appear.
STOPWORDS = {
    "the", "and", "that", "have", "for", "not", "with", "you", "this", "but",
    "his", "her", "hers", "they", "them", "their", "from", "she", "will",
    "would", "there", "been", "were", "what", "when", "which", "who", "whom",
    "into", "than", "then", "some", "could", "should", "other", "about",
    "after", "before", "because", "over", "under", "just", "more", "most",
    "such", "only", "very", "also", "even", "here", "your", "ours", "yours",
    "himself", "herself", "itself", "themselves", "again", "once", "both",
    "each", "does", "did", "had", "has", "was", "are", "is", "be", "being",
    "having", "doing", "while", "where", "why", "how", "all", "any", "few",
    "nor", "own", "same", "too", "can", "may", "might", "must", "shall",
    "upon", "these", "those", "them", "him", "our", "its", "it", "as", "at",
    "by", "of", "on", "or", "to", "in", "if", "so", "no", "do", "an", "a",
    "never", "always", "every", "still", "though", "without", "through",
    "against", "between", "around", "another", "myself", "yourself", "well",
    "back", "down", "out", "up", "off", "away", "much", "many", "made", "make",
    "said", "says", "know", "knew", "think", "thought", "like", "come", "came",
    "went", "goes", "look", "looked", "time", "than", "were", "long", "little",
}

# Below this many words a book is too short for in-book rarity to mean
# anything - every word looks rare in a 300-word sample.
RARITY_MIN_WORDS = 1500


# -------------------------------------------------------------- tokenization

class _Tok:
    """Minimal token, so spaCy and the fallback look identical downstream."""
    __slots__ = ("text", "pos", "is_sent_start", "is_para_end")

    def __init__(self, text: str, pos: str = "X", is_sent_start: bool = False):
        self.text = text
        self.pos = pos
        self.is_sent_start = is_sent_start
        self.is_para_end = False


_FALLBACK_RE = re.compile(r"\w+(?:'\w+)?|[^\w\s]")


def _fallback_tokens(text: str) -> List[List[_Tok]]:
    sentences = []
    for raw_sentence in re.split(r"(?<=[.!?])\s+", text):
        raw_sentence = raw_sentence.strip()
        if not raw_sentence:
            continue
        toks = []
        for i, word in enumerate(_FALLBACK_RE.findall(raw_sentence)):
            pos = "NUM" if word.isdigit() else (
                "PROPN" if word[:1].isupper() and i > 0 else "X")
            toks.append(_Tok(word, pos, is_sent_start=(i == 0)))
        if toks:
            sentences.append(toks)
    return sentences


def _spacy_tokens(text: str, nlp) -> List[List[_Tok]]:
    sentences = []
    # Chunk the text so one huge doc does not blow up memory
    for doc in nlp.pipe(_chunk_text(text, 40_000), batch_size=4):
        for sent in doc.sents:
            toks = []
            for i, token in enumerate(sent):
                if token.is_space:
                    continue
                toks.append(_Tok(token.text, token.pos_, is_sent_start=(i == 0)))
            if toks:
                sentences.append(toks)
    return sentences


def _chunk_text(text: str, size: int) -> Iterable[str]:
    if len(text) <= size:
        yield text
        return
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            cut = text.rfind(" ", start + size // 2, end)
            if cut > start:
                end = cut
        yield text[start:end]
        start = end


# ---------------------------------------------------------------- the engine

class BookAnalyzerPipeline:
    def __init__(self, config: Optional[PenaltyConfig] = None,
                 api_key: Optional[str] = None, model: Optional[str] = None):
        self.config = config or PenaltyConfig()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("FLASHREADER_LLM_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("OPENAI_BASE_URL")

    # ------------------------------------------------------------------ main
    def analyze(self, text: str, use_llm: bool = False,
                max_llm_chunks: int = 12) -> Dict[str, Any]:
        """
        Returns {"tokens": [...], "stats": {...}}.
        This is the only method routes should call.
        """
        nlp = _load_nlp()
        sentences = _spacy_tokens(text, nlp) if nlp else _fallback_tokens(text)

        # Mark the last token of each paragraph, for a longer pause
        self._mark_paragraphs(text, sentences)

        rarity = self._book_rarity(sentences)

        tokens: List[Dict[str, Any]] = []
        for sentence in sentences:
            sentence_penalty = self._sentence_penalty(sentence)
            for tok in sentence:
                penalty = sentence_penalty + self._word_penalty(tok, rarity)
                entry = {"w": tok.text,
                         "i": min(self.config.max_penalty, penalty)}
                pause = self._pause_for(tok)
                if pause:
                    entry["p"] = pause
                tokens.append(entry)

        llm_report = {"used": False}
        if use_llm:
            llm_report = self._apply_llm(text, tokens, max_llm_chunks)

        return {
            "tokens": tokens,
            "stats": {
                "token_count": len(tokens),
                "sentence_count": len(sentences),
                "avg_penalty": round(
                    sum(t["i"] for t in tokens) / max(1, len(tokens)), 1),
                "nlp": nlp_status(),
                "llm": llm_report,
                "config": asdict(self.config),
            },
        }

    # Kept so existing callers do not break.
    def process_text(self, text: str) -> List[Dict[str, Any]]:
        return self.analyze(text)["tokens"]

    # ------------------------------------------------------------- penalties
    def _word_penalty(self, tok: _Tok, rarity: Dict[str, int]) -> int:
        cfg = self.config
        text = tok.text
        penalty = 0

        length = len(text)
        if length >= 11:
            penalty += cfg.word_len_long
        elif length >= 8:
            penalty += cfg.word_len_medium

        if tok.pos == "PROPN":
            penalty += cfg.proper_noun
        elif tok.pos == "NUM" or any(ch.isdigit() for ch in text):
            penalty += cfg.number

        lowered = text.lower()
        count = rarity.get(lowered)
        if count is not None:
            if count <= 2:
                penalty += cfg.rare_in_book
            elif count <= 6:
                penalty += cfg.uncommon_in_book

        if lowered in CONJUNCTIONS:
            penalty += cfg.clause_dense

        if tok.is_sent_start:
            penalty += cfg.sentence_first_word

        if text in ('"', "'"):
            penalty += cfg.dialogue_open

        return penalty

    def _sentence_penalty(self, sentence: List[_Tok]) -> int:
        cfg = self.config
        penalty = 0
        length = len(sentence)

        if length >= 40:
            penalty += cfg.sentence_very_long
        elif length >= 25:
            penalty += cfg.sentence_long

        clauses = sum(1 for t in sentence if t.text in CLAUSE_MARK)
        if clauses >= 3:
            penalty += cfg.clause_dense

        return penalty

    def _pause_for(self, tok: _Tok) -> int:
        cfg = self.config
        if tok.is_para_end:
            return cfg.pause_paragraph
        if tok.text in SENTENCE_END:
            return cfg.pause_sentence
        if tok.text in CLAUSE_MARK:
            return cfg.pause_comma
        return 0

    def _mark_paragraphs(self, text: str, sentences: List[List[_Tok]]) -> None:
        """
        Cheap but reliable: count how many sentences fall inside each
        paragraph by matching sentence order against the source text.
        """
        paragraph_sizes = []
        for para in text.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            count = len([s for s in re.split(r"(?<=[.!?])\s+", para) if s.strip()])
            paragraph_sizes.append(max(1, count))

        index = 0
        for size in paragraph_sizes:
            index += size
            if index - 1 < len(sentences) and sentences[index - 1]:
                sentences[index - 1][-1].is_para_end = True

    def _book_rarity(self, sentences: List[List[_Tok]]) -> Dict[str, int]:
        """
        Word counts for this book only. Returns an empty map for short
        texts, and skips function words, so "that" is never flagged rare.
        """
        counter = Counter()
        total = 0
        for sentence in sentences:
            for tok in sentence:
                if not tok.text.isalpha():
                    continue
                total += 1
                lowered = tok.text.lower()
                if len(lowered) > 4 and lowered not in STOPWORDS:
                    counter[lowered] += 1

        if total < RARITY_MIN_WORDS:
            return {}
        return counter

    # ------------------------------------------------------------------- LLM
    def _apply_llm(self, text: str, tokens: List[Dict[str, Any]],
                   max_chunks: int) -> Dict[str, Any]:
        """
        Asks the model which words and passages genuinely need slowing
        down, then boosts those tokens. Failure here is never fatal: the
        statistical payload is already complete and usable.
        """
        if not self.api_key:
            return {"used": False, "reason": "OPENAI_API_KEY nu este setat"}

        try:
            from openai import OpenAI
        except ImportError:
            return {"used": False, "reason": "pachetul openai nu e instalat"}

        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = OpenAI(**kwargs)

        chunks = list(_chunk_text(text, 6000))[:max_chunks]
        hard_words = set()
        errors = 0

        for chunk in chunks:
            try:
                raw = self._ask_llm(client, chunk)
                data = _parse_json(raw)
                for word in data.get("hard_words", [])[:40]:
                    if isinstance(word, str) and word.strip():
                        hard_words.add(word.strip().lower())
            except Exception:
                errors += 1

        if not hard_words:
            return {"used": True, "hard_words": 0, "chunks": len(chunks),
                    "errors": errors}

        boosted = 0
        cap = self.config.max_penalty
        for token in tokens:
            if token["w"].lower() in hard_words:
                token["i"] = min(cap, token["i"] + self.config.llm_hard_word)
                boosted += 1

        return {"used": True, "hard_words": len(hard_words),
                "tokens_boosted": boosted, "chunks": len(chunks),
                "errors": errors, "model": self.model}

    def _ask_llm(self, client, chunk: str) -> str:
        system = (
            "You analyse prose for a speed-reading device. Identify words and "
            "phrases that a reader must slow down for: rare or technical "
            "vocabulary, proper nouns carrying plot weight, and words at a "
            "surprising or disorienting turn in the text. Reply with JSON "
            'only, no prose, no code fences, shaped exactly as: '
            '{"hard_words": ["word", ...]} with at most 25 entries.')
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": chunk}],
            temperature=0,
            max_tokens=400,
        )
        return response.choices[0].message.content or "{}"


def _parse_json(raw: str) -> Dict[str, Any]:
    """Models still wrap JSON in fences now and then."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise
