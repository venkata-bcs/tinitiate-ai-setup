"""
Build branded PDFs and PNG logos for the fictional companies in this folder.

For every company folder that has a company.yaml:
  * documents/source/*.md  ->  documents/<same-name>.pdf   (branded, via headless Chrome)
  * brand/*.svg            ->  brand/*.png

Usage:
    python _tools/build.py                 # build everything
    python _tools/build.py atlas-retail-bank   # build one company

Requirements: Python 3.10+, `markdown`, `pyyaml`, and Google Chrome or Microsoft Edge.
Set CHROME_PATH if the browser is not in a standard location.
"""
from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent

BROWSER_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
    shutil.which("chrome") or "",
]


def find_browser() -> str:
    for c in BROWSER_CANDIDATES:
        if c and Path(c).exists():
            return c
    sys.exit("Chrome/Edge not found. Set CHROME_PATH.")


def run_browser(args: list[str]) -> None:
    subprocess.run([find_browser(), "--headless=new", "--disable-gpu", *args],
                   check=True, capture_output=True, timeout=120)


FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def read_doc(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONT_MATTER.match(text)
    if not m:
        return {"title": path.stem}, text
    return yaml.safe_load(m.group(1)) or {}, text[m.end():]


CSS = """
@page { size: Letter; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; color: #1d232b; font-size: 10.5pt; line-height: 1.5; margin: 0; }
header.brand { display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid var(--primary); padding-bottom: 8px; }
header.brand svg { height: 46px; width: auto; }
header.brand .meta { text-align: right; font-size: 8.5pt; color: #55606c; }
.cover { margin: 22px 0 18px; padding: 18px 20px; background: var(--tint); border-left: 6px solid var(--accent); }
.cover .docid { font-size: 9pt; letter-spacing: .08em; color: var(--primary); font-weight: 600; text-transform: uppercase; }
.cover h1 { margin: 4px 0 6px; font-size: 21pt; color: var(--primary); line-height: 1.2; }
.cover .subtitle { color: #44505c; font-size: 11pt; }
table.control { width: 100%; border-collapse: collapse; margin: 0 0 18px; font-size: 9pt; }
table.control td { border: 1px solid #cfd6dd; padding: 5px 8px; }
table.control td.k { background: #f3f5f7; font-weight: 600; width: 22%; }
h2 { color: var(--primary); font-size: 13.5pt; margin: 20px 0 6px; border-bottom: 1px solid #dfe4e8; padding-bottom: 3px; break-after: avoid; }
h3 { color: #2b3540; font-size: 11.2pt; margin: 14px 0 4px; break-after: avoid; }
p { margin: 5px 0 8px; }
ul, ol { margin: 4px 0 8px 0; padding-left: 20px; }
li { margin: 2px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 9.3pt; break-inside: avoid; }
th { background: var(--primary); color: #fff; text-align: left; padding: 5px 7px; font-weight: 600; }
td { border-bottom: 1px solid #dde2e7; padding: 5px 7px; vertical-align: top; }
tr:nth-child(even) td { background: #fafbfc; }
blockquote { margin: 10px 0; padding: 8px 12px; background: #fff8e6; border-left: 4px solid var(--accent); color: #3d3d3d; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f1f3f5; padding: 0 3px; }
footer.doc { margin-top: 26px; border-top: 1px solid #cfd6dd; padding-top: 8px; font-size: 8pt; color: #66717c; }
footer.doc .disclaimer { margin-top: 6px; font-style: italic; }
"""


def render_html(company: dict, meta: dict, body_md: str, logo_svg: str) -> str:
    body = markdown.markdown(body_md, extensions=["tables", "sane_lists", "attr_list"])
    c = company
    control_rows = [
        ("Document ID", meta.get("doc_id", "")),
        ("Version", meta.get("version", "1.0")),
        ("Effective date", meta.get("effective", "")),
        ("Next review", meta.get("review", "")),
        ("Policy owner", meta.get("owner", "")),
        ("Approved by", meta.get("approved_by", "")),
        ("Applies to", meta.get("applies_to", "")),
        ("Classification", meta.get("classification", "Public")),
    ]
    rows = []
    for i in range(0, len(control_rows), 2):
        cells = "".join(
            f'<td class="k">{html.escape(k)}</td><td>{html.escape(str(v))}</td>'
            for k, v in control_rows[i:i + 2])
        rows.append(f"<tr>{cells}</tr>")
    hq = c["headquarters"]
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{html.escape(meta.get('title', ''))} - {html.escape(c['legal_name'])}</title>
<style>:root {{ --primary: {c['colors']['primary']}; --accent: {c['colors']['accent']}; --tint: {c['colors']['tint']}; }}
{CSS}</style></head><body>
<header class="brand">{logo_svg}
  <div class="meta">{html.escape(c['legal_name'])}<br>{html.escape(hq['line1'])}, {html.escape(hq['city_line'])}<br>{html.escape(c['website'])}</div>
</header>
<section class="cover">
  <div class="docid">{html.escape(meta.get('category', 'Policy'))} &middot; {html.escape(meta.get('doc_id', ''))}</div>
  <h1>{html.escape(meta.get('title', ''))}</h1>
  <div class="subtitle">{html.escape(meta.get('subtitle', ''))}</div>
</section>
<table class="control">{''.join(rows)}</table>
{body}
<footer class="doc">
  {html.escape(c['legal_name'])} &middot; {html.escape(hq['line1'])}, {html.escape(hq['city_line'])}, {html.escape(hq['country'])} &middot; {html.escape(c['phone'])} &middot; {html.escape(c['website'])}<br>
  Uncontrolled when printed. The current version is on the {html.escape(c['short_name'])} policy portal.
  <div class="disclaimer">{html.escape(c['disclaimer'])}</div>
</footer>
</body></html>"""


def strip_xml_title(svg: str) -> str:
    return re.sub(r"<title>.*?</title>", "", svg, flags=re.S)


def build_company(folder: Path) -> None:
    company = yaml.safe_load((folder / "company.yaml").read_text(encoding="utf-8"))
    logo_svg = strip_xml_title((folder / "brand" / "logo.svg").read_text(encoding="utf-8"))
    src_dir = folder / "documents" / "source"
    out_dir = folder / "documents"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for md in sorted(src_dir.glob("*.md")):
            meta, body = read_doc(md)
            page = tmp / (md.stem + ".html")
            page.write_text(render_html(company, meta, body, logo_svg), encoding="utf-8")
            pdf = out_dir / (md.stem + ".pdf")
            run_browser(["--no-pdf-header-footer", f"--print-to-pdf={pdf}", page.as_uri()])
            print(f"  pdf  {pdf.relative_to(ROOT)}")
        # PNG renders of the brand SVGs
        for svg in sorted((folder / "brand").glob("*.svg")):
            text = svg.read_text(encoding="utf-8")
            vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', text)
            w, h = (float(vb.group(1)), float(vb.group(2))) if vb else (256, 256)
            scale = 512 / max(w, h) if "icon" in svg.stem else 4
            W, H = int(w * scale), int(h * scale)
            page = tmp / (svg.stem + "_png.html")
            page.write_text(
                f'<html><body style="margin:0;background:transparent">'
                f'<img src="{svg.as_uri()}" style="width:{W}px;height:{H}px;display:block"></body></html>',
                encoding="utf-8")
            png = svg.with_suffix(".png")
            run_browser(["--hide-scrollbars", "--default-background-color=00000000",
                         f"--window-size={W},{H}", f"--screenshot={png}", page.as_uri()])
            print(f"  png  {png.relative_to(ROOT)}")


def main() -> None:
    targets = sys.argv[1:]
    for folder in sorted(p for p in ROOT.iterdir() if (p / "company.yaml").exists()):
        if targets and folder.name not in targets:
            continue
        print(folder.name)
        build_company(folder)


if __name__ == "__main__":
    main()
