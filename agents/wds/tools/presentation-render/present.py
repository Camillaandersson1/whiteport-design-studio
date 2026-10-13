#!/usr/bin/env python3
"""
present.py: a folder's presentation.md to presentation.html, a deck you browse with the arrow keys.
Part of WDS (agents/wds/tools/presentation-render.md).

    python present.py <folder>                 # <folder>/presentation.md -> <folder>/presentation.html
    python present.py <folder> --theme <css>   # a specific theme instead of the visual identity
    python present.py --all <project folder>   # every presentation.md below the project

presentation.md starts with a front matter block (title, project, updated, status) and holds one
slide per section, separated by a line with only "---". The look comes from agents/wds/tools/theme.
Requires: markdown, PyYAML.
"""

import html
import io
import re
import sys
from pathlib import Path

import markdown
import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "theme"))
from theme import Theme  # noqa: E402

CSS = """
*{box-sizing:border-box}
html{scroll-snap-type:y mandatory;scroll-behavior:smooth}
body{margin:0;background:var(--wds-paper);color:var(--wds-ink);font:18px/1.6 var(--wds-font-body)}
.slide{min-height:100vh;scroll-snap-align:start;display:flex;flex-direction:column;justify-content:center;
  padding:88px max(32px,8vw) 72px;border-bottom:1px solid var(--wds-line)}
.slide>*{max-width:1100px}
.slide.cover h1{font:400 clamp(44px,6vw,84px)/1.05 var(--wds-font-display);margin:.2em 0 .3em}
.slide.cover .lede{font-size:clamp(19px,2vw,24px);color:var(--wds-ink-2);max-width:56ch}
h1,h2{font:400 clamp(32px,4vw,52px)/1.1 var(--wds-font-display);margin:0 0 .6em}
h3{font:600 20px/1.3 var(--wds-font-body);margin:1.4em 0 .4em}
p,li{max-width:66ch}
ul,ol{padding-left:1.2em} li{margin:.35em 0}
strong{font-weight:600}
blockquote{margin:1em 0;padding-left:18px;border-left:2px solid var(--wds-accent);color:var(--wds-ink-2);font-size:1.15em}
table{border-collapse:collapse;width:100%;font-size:16px;margin:.6em 0}
th,td{text-align:left;vertical-align:top;padding:10px 12px;border-bottom:1px solid var(--wds-line)}
th{font:12px var(--wds-font-mono);letter-spacing:.05em;text-transform:uppercase;color:var(--wds-ink-3);font-weight:400}
img{max-width:100%;height:auto;border:1px solid var(--wds-line);border-radius:var(--wds-radius)}
code{font-family:var(--wds-font-mono);font-size:.9em}
a{color:var(--wds-accent-ink)}
.status{display:inline-block;margin-top:18px;padding:8px 14px;border:1px solid var(--wds-line);border-radius:var(--wds-radius);
  font-size:15px;color:var(--wds-ink-2);max-width:70ch}
.bar{position:fixed;top:0;left:0;right:0;display:flex;justify-content:space-between;gap:16px;padding:18px max(32px,8vw);
  font:12px/1.4 var(--wds-font-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--wds-ink-3);
  background:var(--wds-paper);border-bottom:1px solid var(--wds-line);z-index:2}
.count{position:fixed;right:max(32px,8vw);bottom:20px;font:12px var(--wds-font-mono);color:var(--wds-ink-3)}
.progress{position:fixed;left:0;bottom:0;height:2px;background:var(--wds-accent);transition:width .3s}
@media (max-width:700px){.bar span:last-child{display:none} body{font-size:16px}}
@media print{html{scroll-snap-type:none}.bar,.count,.progress{display:none}.slide{break-after:page;min-height:auto;border:0}}
"""

JS = """
const s=[...document.querySelectorAll('.slide')],c=document.querySelector('.count'),p=document.querySelector('.progress');
let i=0;const go=n=>{i=Math.max(0,Math.min(s.length-1,n));s[i].scrollIntoView({behavior:'smooth'});};
const mark=()=>{c.textContent=(i+1)+' / '+s.length;p.style.width=((i+1)/s.length*100)+'%';};
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){i=s.indexOf(e.target);mark();}}),{threshold:.55});s.forEach(x=>io.observe(x));
addEventListener('keydown',e=>{if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();go(i+1);}
 if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();go(i-1);} if(e.key==='Home')go(0); if(e.key==='End')go(s.length-1);});
mark();
"""


def split(text):
    meta = {}
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        text = text[m.end():]
    slides = [s.strip() for s in re.split(r"^---\s*$", text, flags=re.M) if s.strip()]
    return meta, slides


def render(folder, theme_path=None):
    src = folder / "presentation.md"
    if not src.exists():
        print(f"Ingen presentation.md i {folder}.")
        return False
    meta, slides = split(src.read_text(encoding="utf-8"))
    th = Theme(folder, theme_path)
    md = lambda s: markdown.markdown(s, extensions=["tables", "sane_lists"])  # noqa: E731
    title = meta.get("title", folder.name)
    sections = []
    for n, s in enumerate(slides):
        if n == 0:
            body = md(s)
            if meta.get("status"):
                body += f'<div class="status">{markdown.markdown(str(meta["status"])).removeprefix("<p>").removesuffix("</p>")}</div>'
            sections.append(f'<section class="slide cover" id="s1">{body}</section>')
        else:
            sections.append(f'<section class="slide" id="s{n + 1}">{md(s)}</section>')
    left = " · ".join(str(x) for x in (meta.get("project"), title) if x)
    right = f"Updated {meta['updated']}" if meta.get("updated") else ""
    page = f"""<!doctype html>
<html lang="{meta.get('lang', 'en')}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(left or title)}</title>
{th.style(CSS)}</head>
<body>
<div class="bar"><span>{html.escape(left)}</span><span>{html.escape(right)}</span></div>
{chr(10).join(sections)}
<div class="count"></div><div class="progress"></div>
<script>{JS}</script>
</body></html>
"""
    out = folder / "presentation.html"
    out.write_text(page, encoding="utf-8", newline="\n")
    print(f"{out}  ({len(slides)} bilder, tema: {th.describe()})")
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    elif args[0] == "--all":
        for f in sorted(Path(args[1]).rglob("presentation.md")):
            render(f.parent)
    else:
        render(Path(args[0]), args[args.index("--theme") + 1] if "--theme" in args else None)
