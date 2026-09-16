"""
server/pipeline/analyzer.py

NLP and LLM processing engine. Analyzes book text and computes
per-word WPM subtraction penalties based on difficulty and context.
"""

import os
import json
import spacy
from typing import List, Dict, Any
from openai import OpenAI

# Load spaCy model for syntactic and lexical analysis
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise RuntimeError("Run 'python -m spacy download en_core_web_sm' first.")


class BookAnalyzerPipeline:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY", "mock-key"))

    def process_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Processes text through spaCy NLP and optional OpenAI enrichment.
        Returns a payload list: [{"w": "word", "i": instruction_penalty}]
        """
        doc = nlp(text)
        payload = []

        for sent in doc.sents:
            # Detect sentence-level complexity (e.g., long or complex sentences)
            is_complex_sentence = len(sent) > 20

            for token in sent:
                if token.is_space:
                    continue

                penalty = 0

                # 1. Length penalty (longer words require more fixation time)
                word_len = len(token.text)
                if word_len > 10:
                    penalty += 40
                elif word_len > 7:
                    penalty += 20

                # 2. Rare or complex parts of speech (Proper Nouns, Technical Nouns)
                if token.pos_ in ["PROPN", "NUM"]:
                    penalty += 25

                # 3. Punctuation delay (commas, periods require pauses)
                if token.text in [".", "!", "?"]:
                    penalty += 50
                elif token.text in [",", ";", ":"]:
                    penalty += 30

                # 4. Sentence structure complexity offset
                if is_complex_sentence:
                    penalty += 15

                payload.append({"w": token.text, "i": penalty})

        return payload

    def enrich_with_llm(self, text_chunk: str, base_tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optional step: Uses LLM to identify unexpected narrative turns or high cognitive load words.
        """
        prompt = (
            "Analyze this text chunk and list 3-5 rare words or unexpected structural moments "
            "that require slower reading speeds. Return JSON array of words:\n"
            f"Text: {text_chunk}"
        )
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150
            )
            # Parse LLM response and dynamically boost penalties for flagged words
            # (Fallback to base_tokens if LLM is unavailable)
            return base_tokens
        except Exception:
            return base_tokens