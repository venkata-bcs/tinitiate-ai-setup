"""
Generate the static websites for each fictional company.

    python _tools/build_sites.py

Reads <company>/company.yaml, <company>/website/content.yaml and the front matter of
<company>/documents/source/*.md, and writes plain HTML pages to <company>/website/.
Brand SVGs are copied to <company>/website/assets/.
"""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)

PAGES = [
    ("index.html", "Home"),
    ("about.html", "About"),
    ("services.html", None),          # label comes from content.yaml
    ("policies.html", "Policies & Documents"),
    ("faq.html", "FAQ"),
    ("careers.html", "Careers"),
    ("contact.html", "Contact"),
]

CSS = """:root{--primary:%(primary)s;--accent:%(accent)s;--tint:%(tint)s;--ink:#1d232b;--muted:#5b6672;--line:#e1e6ea;--bg:#ffffff}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%%}
body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg);line-height:1.6}
a{color:var(--primary)}img{max-width:100%%}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}
.notice{background:#fff7db;color:#5a4a00;font-size:13px;text-align:center;padding:6px 16px;border-bottom:1px solid #f0e2a8}
header.site{border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:10}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:72px;flex-wrap:wrap}
header.site .logo img{height:44px;display:block}
nav ul{list-style:none;display:flex;flex-wrap:wrap;gap:4px 18px;margin:0;padding:8px 0}
nav a{text-decoration:none;color:var(--ink);font-weight:500;font-size:15px;padding:6px 0;border-bottom:2px solid transparent}
nav a:hover,nav a.active{border-color:var(--accent);color:var(--primary)}
.hero{background:linear-gradient(120deg,var(--primary),color-mix(in srgb,var(--primary) 70%%,var(--accent)));color:#fff;padding:72px 0 64px}
.hero h1{font-size:clamp(30px,5vw,48px);line-height:1.15;margin:0 0 14px;max-width:760px}
.hero p{font-size:18px;max-width:680px;opacity:.92;margin:0 0 26px}
.btn{display:inline-block;background:var(--accent);color:#fff;text-decoration:none;padding:12px 22px;border-radius:6px;font-weight:600;margin:4px 8px 4px 0}
.btn.ghost{background:transparent;border:2px solid #fff}
.page-head{background:var(--tint);padding:40px 0 30px;border-bottom:1px solid var(--line)}
.page-head h1{margin:0 0 6px;color:var(--primary);font-size:clamp(26px,4vw,38px)}
.page-head p{margin:0;color:var(--muted);max-width:760px}
section{padding:48px 0}
section h2{color:var(--primary);font-size:26px;margin:0 0 18px}
.grid{display:grid;gap:20px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.card{border:1px solid var(--line);border-radius:10px;padding:20px;background:#fff}
.card h3{margin:0 0 8px;color:var(--primary);font-size:18px}
.card p{margin:0;color:var(--muted);font-size:15px}
.stats{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin-top:6px}
.stat{background:var(--tint);border-radius:10px;padding:18px;text-align:center}
.stat b{display:block;font-size:28px;color:var(--primary)}
.stat span{color:var(--muted);font-size:14px}
table{width:100%%;border-collapse:collapse;font-size:15px}
th{background:var(--primary);color:#fff;text-align:left;padding:10px}
td{border-bottom:1px solid var(--line);padding:10px;vertical-align:top}
.table-wrap{overflow-x:auto}
.doc-list a.pdf{font-weight:600;text-decoration:none}
.tag{display:inline-block;background:var(--tint);color:var(--primary);font-size:12px;font-weight:600;padding:2px 8px;border-radius:20px}
details{border:1px solid var(--line);border-radius:8px;padding:14px 18px;margin:0 0 10px;background:#fff}
summary{cursor:pointer;font-weight:600;color:var(--primary)}
details p{margin:10px 0 0;color:var(--ink)}
.news li{margin:0 0 12px}.news time{color:var(--muted);font-size:14px;margin-right:8px}
.callout{border-left:5px solid var(--accent);background:var(--tint);padding:16px 20px;border-radius:0 8px 8px 0}
footer.site{background:#0f1720;color:#c9d1d9;padding:40px 0 24px;font-size:14px}
footer.site a{color:#e6edf3}
footer.site .cols{display:grid;gap:24px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
footer.site h4{color:#fff;margin:0 0 8px}
footer.site .legal{border-top:1px solid #2a3440;margin-top:24px;padding-top:16px;color:#8b98a5}
.tag{white-space:nowrap}
@media (max-width:640px){.wrap{padding:0 16px}.hero{padding:48px 0}section{padding:36px 0}header.site .wrap{padding-top:8px}
.doc-list th:nth-child(n+3),.doc-list td:nth-child(n+3){display:none}nav ul{gap:2px 14px}nav a{font-size:14px}}
"""


def esc(s) -> str:
    return html.escape(str(s))


def doc_meta(path: Path) -> dict:
    m = FRONT.match(path.read_text(encoding="utf-8"))
    return yaml.safe_load(m.group(1)) if m else {"title": path.stem}


def layout(c: dict, content: dict, page: str, title: str, body: str) -> str:
    nav = []
    for fname, label in PAGES:
        label = label or content["services_label"]
        cls = ' class="active"' if fname == page else ""
        nav.append(f'<li><a href="{fname}"{cls}>{esc(label)}</a></li>')
    hq = c["headquarters"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | {esc(c['legal_name'])}</title>
<meta name="description" content="{esc(content['meta_description'])}">
<link rel="icon" href="assets/icon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="notice">Fictional company for AI training and demonstration - not a real business.</div>
<header class="site"><div class="wrap">
  <a class="logo" href="index.html"><img src="assets/logo.svg" alt="{esc(c['legal_name'])} logo"></a>
  <nav aria-label="Main"><ul>{''.join(nav)}</ul></nav>
</div></header>
<main>
{body}
</main>
<footer class="site"><div class="wrap">
  <div class="cols">
    <div><h4>{esc(c['legal_name'])}</h4>{esc(hq['line1'])}<br>{esc(hq['city_line'])}, {esc(hq['country'])}<br>{esc(c['phone'])}<br><a href="mailto:{esc(c['email'])}">{esc(c['email'])}</a></div>
    <div><h4>Explore</h4><a href="about.html">About us</a><br><a href="services.html">{esc(content['services_label'])}</a><br><a href="careers.html">Careers</a><br><a href="contact.html">Locations &amp; contact</a></div>
    <div><h4>Policies</h4><a href="policies.html">All policies &amp; documents</a><br><a href="faq.html">Frequently asked questions</a><br>{content.get('footer_extra', '')}</div>
  </div>
  <div class="legal">&copy; 2026 {esc(c['legal_name'])}. {esc(c['disclaimer'])}</div>
</div></footer>
</body>
</html>
"""


def page_head(title: str, sub: str) -> str:
    return f'<div class="page-head"><div class="wrap"><h1>{esc(title)}</h1><p>{esc(sub)}</p></div></div>'


def cards(items: list[dict]) -> str:
    return '<div class="grid">' + "".join(
        f'<div class="card"><h3>{esc(i["title"])}</h3><p>{esc(i["text"])}</p></div>' for i in items) + "</div>"


def build(folder: Path) -> None:
    c = yaml.safe_load((folder / "company.yaml").read_text(encoding="utf-8"))
    content = yaml.safe_load((folder / "website" / "content.yaml").read_text(encoding="utf-8"))
    site = folder / "website"
    assets = site / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for f in ("logo.svg", "icon.svg"):
        shutil.copyfile(folder / "brand" / f, assets / f)
    (assets / "style.css").write_text(CSS % c["colors"], encoding="utf-8")

    docs = [(p, doc_meta(p)) for p in sorted((folder / "documents" / "source").glob("*.md"))]
    pages: dict[str, tuple[str, str]] = {}

    # ---- Home
    h = content["home"]
    stats = "".join(f'<div class="stat"><b>{esc(s["value"])}</b><span>{esc(s["label"])}</span></div>' for s in h["stats"])
    news = "".join(f'<li><time>{esc(n["date"])}</time>{esc(n["text"])}</li>' for n in h["news"])
    featured = "".join(
        f'<li><a href="../documents/{p.stem}.pdf">{esc(m["title"])}</a> <span class="tag">{esc(m["doc_id"])}</span></li>'
        for p, m in [d for d in docs if d[1].get("classification", "Public").startswith("Public")][:6])
    body = f"""<div class="hero"><div class="wrap"><h1>{esc(h['headline'])}</h1><p>{esc(h['intro'])}</p>
<a class="btn" href="{esc(h['cta_href'])}">{esc(h['cta'])}</a><a class="btn ghost" href="policies.html">Read our policies</a></div></div>
<section><div class="wrap"><h2>{esc(c['short_name'])} at a glance</h2><div class="stats">{stats}</div></div></section>
<section style="background:var(--tint)"><div class="wrap"><h2>{esc(h['features_title'])}</h2>{cards(h['features'])}</div></section>
<section><div class="wrap grid">
  <div><h2>Latest news</h2><ul class="news">{news}</ul></div>
  <div><h2>Customer documents</h2><ul>{featured}</ul></div>
</div></section>"""
    pages["index.html"] = ("Home", body)

    # ---- About
    a = content["about"]
    leaders = "".join(f"<tr><td>{esc(l['name'])}</td><td>{esc(l['title'])}</td></tr>" for l in c["leadership"])
    timeline = "".join(f"<tr><td><b>{esc(t['year'])}</b></td><td>{esc(t['event'])}</td></tr>" for t in a["timeline"])
    body = page_head("About " + c["short_name"], a["summary"]) + f"""
<section><div class="wrap"><h2>Our story</h2>{''.join(f'<p>{esc(p)}</p>' for p in a['story'])}
<div class="callout"><b>Mission:</b> {esc(a['mission'])}</div></div></section>
<section style="background:var(--tint)"><div class="wrap"><h2>Our values</h2>{cards(a['values'])}</div></section>
<section><div class="wrap"><h2>Milestones</h2><div class="table-wrap"><table><tr><th>Year</th><th>Milestone</th></tr>{timeline}</table></div></div></section>
<section><div class="wrap"><h2>Leadership team</h2><div class="table-wrap"><table><tr><th>Name</th><th>Role</th></tr>{leaders}</table></div></div></section>"""
    pages["about.html"] = ("About", body)

    # ---- Services
    s = content["services"]
    groups = "".join(f'<section><div class="wrap"><h2>{esc(g["group"])}</h2>{cards(g["items"])}</div></section>' for g in s["groups"])
    pages["services.html"] = (content["services_label"], page_head(content["services_label"], s["summary"]) + groups)

    # ---- Policies
    by_cat: dict[str, list] = {}
    for p, m in docs:
        by_cat.setdefault(m.get("category", "Policy"), []).append((p, m))
    sections = []
    for cat, items in by_cat.items():
        rows = "".join(
            f'<tr><td><a class="pdf" href="../documents/{p.stem}.pdf">{esc(m["title"])}</a><br><small>{esc(m.get("subtitle", ""))}</small></td>'
            f'<td><span class="tag">{esc(m["doc_id"])}</span></td><td>{esc(m.get("version", ""))}</td>'
            f'<td>{esc(m.get("effective", ""))}</td><td>{esc(m.get("classification", ""))}</td></tr>' for p, m in items)
        sections.append(f'<h2>{esc(cat)}</h2><div class="table-wrap doc-list"><table><tr><th>Document</th><th>ID</th><th>Version</th><th>Effective</th><th>Classification</th></tr>{rows}</table></div><br>')
    body = page_head("Policies & Documents", content["policies_intro"]) + f'<section><div class="wrap">{"".join(sections)}</div></section>'
    pages["policies.html"] = ("Policies & Documents", body)

    # ---- FAQ
    faqs = "".join(f"<details><summary>{esc(q['q'])}</summary><p>{esc(q['a'])}</p></details>" for q in content["faq"])
    pages["faq.html"] = ("FAQ", page_head("Frequently asked questions", content["faq_intro"]) + f'<section><div class="wrap">{faqs}</div></section>')

    # ---- Careers
    cr = content["careers"]
    jobs = "".join(f"<tr><td><b>{esc(j['title'])}</b></td><td>{esc(j['location'])}</td><td>{esc(j['type'])}</td><td>{esc(j['ref'])}</td></tr>" for j in cr["jobs"])
    body = page_head("Careers", cr["summary"]) + f"""
<section><div class="wrap"><h2>Why work with us</h2>{cards(cr['benefits'])}</div></section>
<section style="background:var(--tint)"><div class="wrap"><h2>Open positions</h2><div class="table-wrap"><table><tr><th>Role</th><th>Location</th><th>Type</th><th>Ref.</th></tr>{jobs}</table></div>
<p>{esc(cr['eeo'])}</p></div></section>"""
    pages["careers.html"] = ("Careers", body)

    # ---- Contact
    ct = content["contact"]
    loc_rows = "".join(
        "<tr>" + "".join(f"<td>{esc(l.get(k, ''))}</td>" for k in ct["location_fields"]) + "</tr>"
        for l in c[ct["location_source"]])
    heads = "".join(f"<th>{esc(h)}</th>" for h in ct["location_headers"])
    lines = "".join(f"<tr><td><b>{esc(x['name'])}</b></td><td>{esc(x['value'])}</td><td>{esc(x['hours'])}</td></tr>" for x in ct["lines"])
    body = page_head("Locations & contact", ct["summary"]) + f"""
<section><div class="wrap"><h2>Contact us</h2><div class="table-wrap"><table><tr><th>Service</th><th>Contact</th><th>Hours</th></tr>{lines}</table></div></div></section>
<section style="background:var(--tint)"><div class="wrap"><h2>{esc(ct['locations_title'])}</h2><div class="table-wrap"><table><tr>{heads}</tr>{loc_rows}</table></div></div></section>"""
    pages["contact.html"] = ("Locations & contact", body)

    for fname, (title, body) in pages.items():
        (site / fname).write_text(layout(c, content, fname, title, body), encoding="utf-8")
        print(f"  html {(site / fname).relative_to(ROOT)}")


if __name__ == "__main__":
    for folder in sorted(p for p in ROOT.iterdir() if (p / "company.yaml").exists()):
        print(folder.name)
        build(folder)
