"""Review page on a fake album at http://127.0.0.1:8799/a/fixture. No real photo.

The photos come from stock/ (Unsplash, gitignored); without them, generated color blocks.
"""
import random
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here.parents[1]))
import revela  # noqa: E402

d = here / "albums" / "fixture"
shutil.rmtree(d, ignore_errors=True)
day = d / "photos" / "2026-01-10"
day.mkdir(parents=True)
rnd = random.Random(4)


def blocks(k):
    w, h = (1500, 1000) if k % 4 else (1000, 1500)
    im = Image.new("RGB", (w, h), tuple(rnd.randint(40, 220) for _ in range(3)))
    ImageDraw.Draw(im).ellipse((w * .3, h * .25, w * .7, h * .7), fill=tuple(rnd.randint(40, 220) for _ in range(3)))
    return im


stock = sorted((here / "stock").glob("*.jpg"))
images = [ImageOps.exif_transpose(Image.open(p)).convert("RGB") for p in stock] or [blocks(k) for k in range(40)]
# A burst of three near-identical shots, one blurry and one dark, so every group on the page shows.
base = images[0]
extra = [("similar", base.crop((30, 20, base.width - 10, base.height))), ("similar", base.crop((0, 0, base.width - 40, base.height - 25))),
         ("blur", base.filter(ImageFilter.GaussianBlur(12))), ("dark", ImageEnhance.Brightness(images[1]).enhance(.08))]

scores = {}
for k, (kind, im) in enumerate([("", im) for im in images] + extra):
    i = f"2026-01-10/{'STOCK' if stock else 'BLOCK'}_{k:02d}.jpg"  # a name per source: /img is cached for an hour
    im.save(day / i.split("/")[1], quality=85)
    emb = [0.0] * 512
    emb[0 if kind == "similar" or k == 0 else k % 512] = 1.0
    t = 1736500000 + (k * 600 if not kind else 20 * (k - len(images) + 1))  # the burst sits next to its original
    scores[i] = {"t": t, "w": im.width, "h": im.height,
                 "faces": [{"box": [0.4, 0.2, 0.6, 0.5], "smile": .5, "blink": .1}],
                 "sharp": 1 if kind == "blur" else 1000, "mean": 8 if kind == "dark" else 120,
                 "aes": 4 + rnd.random() * 3, "cry": .1, "emb": emb}
revela.save(d, "scores.json", scores)
revela.save(d, "picks.json", {})
book = revela.build(d, "square-30", "pocket", 14)  # less room than photos, so some go out
picks = revela.load(d, "picks.json")
picks[book["spreads"][1]["slots"][0]["id"]].update(pick="out", by="user")  # shows a removal by the user
revela.save(d, "picks.json", picks)

revela.ALBUMS = d.parent
import uvicorn  # noqa: E402

_run = uvicorn.run  # 8765 belongs to the real review container
uvicorn.run = lambda app, **k: _run(app, host="127.0.0.1", port=8799, log_level="warning")
revela.review(SimpleNamespace())
