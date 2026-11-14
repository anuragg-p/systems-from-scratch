"""Render each figure through the real sanitizer, light and dark side by side, and screenshot it.

usage: python3 preview.py [name-prefix ...]
"""
import glob
import os
import re
import subprocess
import sys

REPO = os.path.expanduser("~/Documents/WORK/misc/systems-from-scratch")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "preview")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sys.path.insert(0, REPO)
from harness.web import art  # noqa: E402

css = open(os.path.join(REPO, "harness/web/app.css")).read()
root_vars = re.search(r":root \{.*?\n\}", css, re.S).group(0)
dark_vars = re.search(r':root\[data-theme="dark"\] \{.*?\n\}', css, re.S).group(0)
art_rules = "\n".join(l for l in css.splitlines() if l.startswith(".art"))
fonts = os.path.join(REPO, "harness/web/fonts")
head = f"""<style>
@font-face {{ font-family: "Figtree"; src: url(file://{fonts}/Figtree.woff2) format("woff2"); font-weight: 300 900; }}
@font-face {{ font-family: "Geist Mono"; src: url(file://{fonts}/GeistMonoVariable.woff2) format("woff2"); font-weight: 100 900; }}
{root_vars}
.dark {dark_vars.split('{', 1)[1].rsplit('}', 1)[0].join(['{', '}'])}
body {{ margin: 0; display: flex; }}
.pane {{ background: var(--bg); color: var(--fg1); padding: 20px; width: 640px; font: 400 15px/1.55 var(--sans); }}
{art_rules}
</style>"""


def main():
    os.makedirs(OUT, exist_ok=True)
    pats = sys.argv[1:] or [""]
    files = sorted(glob.glob(os.path.join(REPO, "tracks/xv6/lessons/0[67]-*/figures/*.svg")))
    for f in files:
        name = os.path.basename(f)[:-4]
        if not any(name.startswith(p) for p in pats):
            continue
        src = open(f).read()
        clean = art.sanitize(src, prefix="pv")
        if not clean:
            print("SANITIZER REJECTED", f)
            continue
        h = int(re.search(r'viewBox="0 0 640 (\d+)"', src).group(1))
        page = (f"<!doctype html><html><head><meta charset='utf-8'>{head}</head><body>"
                f"<div class='pane'><figure class='art fig' style='margin:0'>{clean}</figure></div>"
                f"<div class='pane dark'><figure class='art fig' style='margin:0'>{clean.replace('pv-', 'pd-')}</figure></div>"
                f"</body></html>")
        hp = os.path.join(OUT, name + ".html")
        open(hp, "w").write(page)
        png = os.path.join(OUT, name + ".png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                        "--force-device-scale-factor=2", f"--window-size=1360,{h + 140}", f"--screenshot={png}",
                        "file://" + hp], capture_output=True)
        print(png)


if __name__ == "__main__":
    main()
