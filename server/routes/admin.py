"""
server/routes/admin.py

A single no-framework page at /admin for putting books into the store:
pick a .pdf or .txt, give it a title, optionally tick the LLM pass, done.
Far quicker than curl while you are testing the pipeline.
"""

import html

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from server.database import get_db
from server.models import Book
from server.pipeline.analyzer import nlp_status

router = APIRouter(tags=["Admin"])

PAGE = """<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FlashReader - administrare</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         max-width: 860px; margin: 0 auto; padding: 24px; line-height: 1.5; }}
  h1 {{ margin-bottom: 4px; }}
  .muted {{ color: #777; font-size: 14px; }}
  form {{ border: 1px solid #8884; border-radius: 12px; padding: 18px;
         margin: 20px 0; display: grid; gap: 12px; }}
  label {{ display: grid; gap: 4px; font-size: 14px; }}
  input[type=text], input[type=number], input[type=file] {{
      padding: 10px; border: 1px solid #8886; border-radius: 8px;
      font-size: 15px; background: transparent; color: inherit; }}
  .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  button {{ padding: 12px 18px; border-radius: 8px; border: none;
           background: #10893e; color: #fff; font-size: 15px; cursor: pointer; }}
  button.link {{ background: transparent; color: #c62828; padding: 4px 8px;
                border: 1px solid #c62828; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 8px 6px; border-bottom: 1px solid #8883;
           font-size: 14px; vertical-align: top; }}
  .check {{ display: flex; align-items: center; gap: 8px; font-size: 14px; }}
</style>
</head>
<body>
<h1>FlashReader</h1>
<p class="muted">Motor NLP: {nlp}</p>

<form action="/store/upload/file" method="post" enctype="multipart/form-data">
  <strong>Adauga o carte</strong>
  <label>Fisier (.pdf, .txt, .md)
    <input type="file" name="file" accept=".pdf,.txt,.md" required>
  </label>
  <div class="row">
    <label>Titlu <input type="text" name="title" required></label>
    <label>Autor <input type="text" name="author" value="Necunoscut"></label>
  </div>
  <div class="row">
    <label>Pret <input type="number" name="price" step="0.01" value="0"></label>
    <label>ID (optional) <input type="text" name="book_id" placeholder="se genereaza din titlu"></label>
  </div>
  <label class="check">
    <input type="checkbox" name="use_llm" value="true">
    Analiza suplimentara cu LLM (necesita OPENAI_API_KEY, dureaza mai mult)
  </label>
  <button type="submit">Incarca si analizeaza</button>
</form>

<h2>Carti in catalog</h2>
{table}

<script>
async function del(id) {{
  if (!confirm("Stergi " + id + "?")) return;
  await fetch("/store/books/" + id, {{ method: "DELETE" }});
  location.reload();
}}
async function reanalyze(id) {{
  const btn = event.target; btn.disabled = true; btn.textContent = "...";
  await fetch("/store/books/" + id + "/reanalyze", {{ method: "POST" }});
  location.reload();
}}
</script>
</body>
</html>
"""


@router.get("/admin", response_class=HTMLResponse)
def admin_page(db: Session = Depends(get_db)):
    books = db.query(Book).order_by(Book.created_at.desc()).all()

    if not books:
        table = '<p class="muted">Catalogul este gol.</p>'
    else:
        rows = []
        for b in books:
            rows.append(
                "<tr>"
                f"<td><strong>{html.escape(b.title or '')}</strong><br>"
                f'<span class="muted">{html.escape(b.author or "")} - '
                f'{html.escape(b.id)}</span></td>'
                f"<td>{b.word_count or 0}</td>"
                f"<td>{round(b.avg_penalty or 0, 1)}</td>"
                f"<td>{html.escape(b.source or '')}"
                f"{' + LLM' if b.analyzed_with_llm else ''}</td>"
                f'<td><a href="/store/books/{html.escape(b.id)}/preview">preview</a></td>'
                f'<td><button class="link" onclick="reanalyze(\'{html.escape(b.id)}\')">re-analiza</button> '
                f'<button class="link" onclick="del(\'{html.escape(b.id)}\')">sterge</button></td>'
                "</tr>"
            )
        table = ("<table><tr><th>Carte</th><th>Cuvinte</th><th>Penalizare medie</th>"
                 "<th>Sursa</th><th></th><th></th></tr>" + "".join(rows) + "</table>")

    return HTMLResponse(PAGE.format(nlp=html.escape(nlp_status()), table=table))
