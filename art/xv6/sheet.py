"""Stack light and dark shots of the given lessons into contact sheets (scaled to 1/2)."""
import sys, glob, os
from PIL import Image
d, out = sys.argv[1], sys.argv[2]
ids = sys.argv[3:]
for lid in ids:
    for n in range(1, 4):
        pair = [os.path.join(d, f"{lid}-fig{n}-{t}.png") for t in ("light", "dark")]
        if not all(os.path.exists(p) for p in pair):
            continue
        ims = [Image.open(p) for p in pair]
        ims = [im.resize((im.width // 2, im.height // 2)) for im in ims]
        w = sum(im.width for im in ims) + 10
        h = max(im.height for im in ims)
        sheet = Image.new("RGB", (w, h), (128, 128, 128))
        x = 0
        for im in ims:
            sheet.paste(im, (x, 0)); x += im.width + 10
        sheet.save(os.path.join(out, f"sheet-{lid}-fig{n}.png"))
