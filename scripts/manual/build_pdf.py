"""Monta o manual do sistema (docs/manual/content/*.md + screenshots) em um PDF unico.

Uso:
    python scripts/manual/build_pdf.py

Le todos os .md de docs/manual/content/ (em ordem alfabetica de arquivo),
converte para HTML, monta uma capa + sumario + capitulos, e exporta
docs/manual/MANUAL_SISTEMA_AGRISDATA.pdf usando o Chromium do Playwright
(mesma engine ja usada nos testes e2e do projeto).

Os arquivos .md devem referenciar imagens com caminho relativo a partir de
docs/manual/, ex: ![Lista de solicitacoes](screenshots/compras/02-solicitacoes-lista.png)
"""
import datetime
from pathlib import Path

import markdown

MANUAL_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "manual"
CONTENT_DIR = MANUAL_DIR / "content"
BUILD_HTML = MANUAL_DIR / "_build.html"
OUTPUT_PDF = MANUAL_DIR / "MANUAL_AGRISDATA.pdf"
LOGO_PATH = MANUAL_DIR.parent.parent / "static" / "img" / "logo.png"

CSS = """
@page { margin: 0; }
* { box-sizing: border-box; }
body {
  font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
  color: #1f2937;
  font-size: 13px;
  line-height: 1.55;
  margin: 0;
}
.cover {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #10231a 0%, #1a7a3c 100%);
  color: #fff;
  page-break-after: always;
  text-align: center;
}
.cover img { width: 280px; margin-bottom: 32px; }
.cover h1 { font-size: 34px; margin: 0 0 8px; }
.cover p { font-size: 15px; opacity: .85; margin: 4px 0; }

.toc { page-break-after: always; padding: 48px 56px; }
.toc h1 { color: #1a7a3c; border-bottom: 2px solid #1a7a3c; padding-bottom: 8px; }
.toc ul { list-style: none; padding-left: 0; }
.toc li { margin: 6px 0; }
.toc a { color: #1f2937; text-decoration: none; }
.toc a:hover { color: #1a7a3c; }
.toc .h2-toc { padding-left: 20px; font-size: 13px; color: #4b5563; }

.chapter { padding: 20px 56px 56px; }
.chapter h1 {
  color: #fff; background: #1a7a3c; margin: 0 -56px 24px; padding: 20px 56px;
  page-break-before: always; font-size: 26px;
}
.chapter > h1:first-child { page-break-before: auto; }
h2 { color: #1a7a3c; border-bottom: 1px solid #d1e7d6; padding-bottom: 6px; margin-top: 36px; }
h3 { color: #14532d; margin-top: 24px; }
figure { margin: 20px 0; page-break-inside: avoid; }
figure img {
  max-width: 100%; border: 1px solid #e5e7eb; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,.08);
}
figcaption { font-size: 12px; color: #6b7280; font-style: italic; margin-top: 6px; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; }
th, td { border: 1px solid #e5e7eb; padding: 6px 10px; text-align: left; }
th { background: #f0f7f2; color: #14532d; }
code { background: #f3f4f6; padding: 1px 5px; border-radius: 4px; font-size: 13px; }
blockquote { border-left: 3px solid #1a7a3c; margin: 16px 0; padding: 4px 16px; color: #4b5563; background: #f9fafb; }
"""


def build_toc_html(sections):
    items = []
    for slug, title, subheadings in sections:
        items.append(f'<li><a href="#{slug}"><strong>{title}</strong></a></li>')
        for sub_id, sub_title in subheadings:
            items.append(f'<li class="h2-toc"><a href="#{sub_id}">{sub_title}</a></li>')
    return "<ul>" + "".join(items) + "</ul>"


def main():
    md_files = sorted(CONTENT_DIR.glob("*.md"))
    if not md_files:
        raise SystemExit(f"Nenhum arquivo .md encontrado em {CONTENT_DIR}")

    chapters_html = []
    toc_sections = []

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        converter = markdown.Markdown(extensions=["tables", "fenced_code", "toc"], extension_configs={
            "toc": {"anchorlink": False}
        })
        html = converter.convert(text)
        toc_tokens = getattr(converter, "toc_tokens", [])

        chapter_title = toc_tokens[0]["name"] if toc_tokens else md_file.stem
        chapter_slug = toc_tokens[0]["id"] if toc_tokens else md_file.stem
        subheadings = [
            (t["id"], t["name"])
            for t in (toc_tokens[0].get("children", []) if toc_tokens else [])
        ]
        toc_sections.append((chapter_slug, chapter_title, subheadings))
        chapters_html.append(f'<section class="chapter">{html}</section>')

    logo_uri = LOGO_PATH.as_uri() if LOGO_PATH.exists() else ""
    today = datetime.date.today().strftime("%d/%m/%Y")

    full_html = f"""<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manual do Sistema - AgrisData</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
  <div class="cover">
    {f'<img src="{logo_uri}">' if logo_uri else ''}
    <h1>Manual do Sistema</h1>
    <p>AgrisData &mdash; Gestão Agrícola Inteligente</p>
    <p>Gerado em {today}</p>
  </div>
  <div class="toc">
    <h1>Sumário</h1>
    {build_toc_html(toc_sections)}
  </div>
  {''.join(chapters_html)}
</body>
</html>"""

    BUILD_HTML.write_text(full_html, encoding="utf-8")
    print(f"HTML intermediario: {BUILD_HTML}")

    from playwright.sync_api import sync_playwright

    tmp_pdf = MANUAL_DIR / "_build_tmp.pdf"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(BUILD_HTML.as_uri())
        page.wait_for_timeout(500)
        page.pdf(
            path=str(tmp_pdf),
            format="A4",
            print_background=True,
            margin={"top": "18mm", "bottom": "16mm", "left": "0mm", "right": "0mm"},
            display_header_footer=True,
            header_template='<span></span>',
            footer_template=(
                '<div style="font-size:9px; color:#9ca3af; width:100%; '
                'text-align:center; padding-top:4px;">'
                'Manual do Sistema - AgrisData &middot; pagina '
                '<span class="pageNumber"></span> de <span class="totalPages"></span></div>'
            ),
        )
        browser.close()

    try:
        tmp_pdf.replace(OUTPUT_PDF)
        print(f"PDF gerado: {OUTPUT_PDF}")
    except PermissionError:
        fallback = MANUAL_DIR / f"MANUAL_SISTEMA_AGRISDATA_{datetime.datetime.now():%H%M%S}.pdf"
        tmp_pdf.replace(fallback)
        print(f"AVISO: {OUTPUT_PDF} esta aberto/travado por outro programa (feche-o).")
        print(f"PDF gerado em arquivo alternativo: {fallback}")


if __name__ == "__main__":
    main()
