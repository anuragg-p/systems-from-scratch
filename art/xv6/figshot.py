"""Screenshot every inline figure of the given lessons, light and dark.

usage: figshot.py PORT OUTDIR LESSON_ID... [--themes light,dark] [--page]
"""
import sys
from playwright.sync_api import sync_playwright

port, out = sys.argv[1], sys.argv[2]
args = [a for a in sys.argv[3:] if not a.startswith("--")]
themes = ["light", "dark"]
for a in sys.argv[3:]:
    if a.startswith("--themes="):
        themes = a.split("=", 1)[1].split(",")
page_shot = "--page" in sys.argv
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME)
    for theme in themes:
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        ctx.add_init_script(f"try{{localStorage.setItem('theme','{theme}')}}catch(e){{}}")
        pg = ctx.new_page()
        for lid in args:
            pg.goto(f"http://127.0.0.1:{port}/t/xv6/{lid}", wait_until="networkidle")
            pg.wait_for_timeout(400)
            figs = pg.query_selector_all("figure.art.fig")
            for i, el in enumerate(figs):
                el.evaluate("e => e.scrollIntoView({block: 'center'})"); pg.wait_for_timeout(150)
                el.screenshot(path=f"{out}/{lid}-fig{i + 1}-{theme}.png")
            if page_shot:
                pg.screenshot(path=f"{out}/{lid}-page-{theme}.png", full_page=True)
            print(lid, theme, len(figs), "figures")
        ctx.close()
    b.close()
