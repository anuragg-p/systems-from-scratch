"""usage: shot.py out.png width url [dark] [full] [clip=selector] [h=900]
Headless Chrome through Playwright; the viewport is set with CDP device emulation,
so a 390px width is a true 390px layout (mobile=True below 700px)."""
import json
import sys
from playwright.sync_api import sync_playwright

out, w, url = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rest = sys.argv[4:]
dark = "dark" in rest
full = "full" in rest
clip = next((a[5:] for a in rest if a.startswith("clip=")), None)
h = int(next((a[2:] for a in rest if a.startswith("h=")), "900"))
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if w < 700 else 1,
                        is_mobile=w < 700, has_touch=w < 700)
    pg = ctx.new_page()
    if dark:
        pg.add_init_script("try{localStorage.setItem('theme','dark')}catch(e){}")
    pg.goto(url, wait_until="load", timeout=40000)
    pg.wait_for_timeout(600)
    m = pg.evaluate("""() => { const vw = document.documentElement.clientWidth; const wide = [];
      for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > vw + 1 && !el.closest('.side')) wide.push(el.tagName.toLowerCase() + '.' + (typeof el.className === 'string' ? el.className : '')); }
      return {vw, docW: document.documentElement.scrollWidth, wide: wide.slice(0, 10)}; }""")
    print(json.dumps(m))
    if clip:
        pg.locator(clip).first.screenshot(path=out)
    else:
        pg.screenshot(path=out, full_page=full)
    b.close()
