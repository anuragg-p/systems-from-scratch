"""usage: covers.py outdir [dark] [ids...]: clip every outline cover from the running site on :8461."""
import sys
from playwright.sync_api import sync_playwright
out = sys.argv[1]
dark = "dark" in sys.argv[2:]
want = [a for a in sys.argv[2:] if a != "dark"]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
    if dark:
        pg.add_init_script("try{localStorage.setItem('theme','dark')}catch(e){}")
    for tid in ("inference", "research"):
        pg.goto(f"http://127.0.0.1:8461/t/{tid}", wait_until="load")
        pg.wait_for_timeout(400)
        for m in range(8):
            key = f"{tid[0]}{m:02d}"
            if want and key not in want:
                continue
            pg.locator(f"#m-{m:02d} .art").screenshot(path=f"{out}/{key}{'-dark' if dark else ''}.png")
    b.close()
