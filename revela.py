#!/usr/bin/env python3
"""Turns an iCloud album into a photobook. No photo leaves this machine.

  revela make ALBUM      score the photos, pick them and lay the book out
  revela release ALBUM   render the book: one JPEG per spread and book.pdf
  revela review          review page at http://127.0.0.1:8765
"""
import argparse
import json
import re
import sys
import threading
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Literal

import layout
import pick

DATA = Path("/data")
ALBUMS = DATA / "albums"
EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
URL = "http://127.0.0.1:8765"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load(d, name, default=None):
    f = d / name
    return json.loads(f.read_text()) if f.exists() else default


def save(d, name, data):
    tmp = d / (name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    tmp.replace(d / name)


def photos(d):
    # icloudpd writes the capture time to the mtime, and the sync keeps it.
    root = d / "photos"
    files = [p for p in root.rglob("*") if p.suffix.lower() in EXTS and not p.name.startswith(".")]
    return {str(p.relative_to(root)): p for p in sorted(files, key=lambda p: (p.stat().st_mtime, str(p)))}


def short(i):
    return Path(i).stem


def reason_kind(why):
    # The review page saves a removal with no reason.
    return why.split(" ")[0] if why.startswith("similar") else why or "removed by you"


def build(d, fmt, style, spreads):
    cache, favs = load(d, "scores.json", {}), d / "favorites.txt"
    scores = {i: cache[i] for i in photos(d) if i in cache}
    favs = set(favs.read_text().split()) if favs.exists() else set()
    picks = pick.choose(scores, load(d, "picks.json", {}), favs, layout.STYLES[style]["per_spread"], spreads)
    save(d, "picks.json", picks)
    book = layout.layout([{"id": i, "w": s["w"], "h": s["h"], "faces": [f["box"] for f in s["faces"]],
                           "hero": picks[i]["hero"]} for i, s in scores.items() if picks[i]["pick"] == "in"], fmt, style)
    book["target_spreads"] = spreads
    save(d, "book.json", book)
    return book


def summary(d, name, book):
    picks = load(d, "picks.json", {})
    n_in = sum(len(s["slots"]) for s in book["spreads"])
    outs = Counter(reason_kind(p["why"]) for p in picks.values() if p["pick"] == "out")
    heroes = sum(p.get("hero", False) for p in picks.values())
    print(f"{name}: {len(picks)} photos, {n_in} in the book, {len(book['spreads'])} spreads "
          f"({book['format']}, {book['style']}), {heroes} heroes.")
    if outs:
        print("Left out: " + ", ".join(f"{n} {k}" for k, n in outs.most_common()) + ".")
    print(f"Review: {URL}/a/{d.name}")


def album_dir(name):
    d = ALBUMS / slug(name)
    if not d.is_dir():
        known = ", ".join(sorted(p.name for p in ALBUMS.glob("*") if p.is_dir())) or "none"
        sys.exit(f"No album {name!r} in {ALBUMS}. Known albums: {known}. The sync creates the album folder.")
    return d


def make(a):
    from score import score_all

    d = album_dir(a.album)
    ps = photos(d)
    if not ps:
        sys.exit(f"No photos in {d / 'photos'}. Run the sync first.")
    cache = load(d, "scores.json", {})
    score_all(ps, cache)
    save(d, "scores.json", cache)
    summary(d, a.album, build(d, a.format, a.style, a.spreads))


def release(a):
    d = album_dir(a.album)
    book = load(d, "book.json")
    if not book:
        sys.exit(f"No book for {a.album!r} yet. Run make first.")
    print(layout.render(book, d / "photos", d / "print"))


def review(a):
    # Imported here: make and release do not need the server.
    import uvicorn
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import FileResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from PIL import Image, ImageOps
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    here = Path(__file__).resolve().parent
    templates = Jinja2Templates(here / "templates")
    lock = threading.Lock()
    app = FastAPI()
    # Blocks DNS rebinding: an outside site cannot read the photos through the browser.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.mount("/static", StaticFiles(directory=here / "static"), name="static")

    def album(s):
        d = ALBUMS / s
        return d if re.fullmatch(r"[a-z0-9-]+", s) and (d / "book.json").exists() else None

    @app.get("/")
    def index(request: Request):
        books = sorted(p.parent.name for p in ALBUMS.glob("*/book.json"))
        if len(books) == 1:
            return RedirectResponse(f"/a/{books[0]}")
        return templates.TemplateResponse(request, "index.html", {"books": books})

    @app.get("/a/{s}")
    def page(request: Request, s: str):
        d = album(s)
        if not d:
            return Response(status_code=404)
        book, picks = load(d, "book.json"), load(d, "picks.json", {})
        in_book = {sl["id"] for sp in book["spreads"] for sl in sp["slots"]}
        removed = {i for i in in_book if picks.get(i, {}).get("pick") == "out"}
        added = [i for i, p in picks.items() if p["pick"] == "in" and i not in in_book]
        groups = {}
        for i, p in picks.items():
            if p["pick"] == "out" and i not in in_book:
                groups.setdefault(reason_kind(p["why"]), []).append((i, p["why"]))
        return templates.TemplateResponse(request, "review.html", {
            "slug": s, "book": book, "removed": removed, "added": added, "short": short,
            "groups": sorted(groups.items(), key=lambda g: -len(g[1])),
            "n_in": len(in_book) - len(removed), "pdf": (d / "print" / "book.pdf").exists()})

    @app.post("/a/{s}/pick/{choice}/{photo:path}")
    def set_pick(s: str, choice: Literal["in", "out"], photo: str):
        d = album(s)
        with lock:
            picks = load(d, "picks.json", {}) if d else {}
            if photo not in picks:
                return Response(status_code=404)
            picks[photo].update(pick=choice, by="user")
            save(d, "picks.json", picks)
        return Response(status_code=204)

    @app.post("/a/{s}/rebuild")
    def rebuild(s: str):
        d = album(s)
        if not d:
            return Response(status_code=404)
        with lock:
            book = load(d, "book.json")
            build(d, book["format"], book["style"], book.get("target_spreads"))
        return Response(status_code=204)

    @app.get("/a/{s}/book.pdf")
    def pdf(s: str):
        d = album(s)
        f = d / "print" / "book.pdf" if d else None
        return FileResponse(f, media_type="application/pdf") if f and f.exists() else Response(status_code=404)

    @app.get("/img/{s}/{photo:path}")
    def image(s: str, photo: str, size: int = 1200):
        root = (ALBUMS / s / "photos").resolve()
        p = (root / photo).resolve()
        if not re.fullmatch(r"[a-z0-9-]+", s) or not p.is_relative_to(root) or not p.is_file():
            return Response(status_code=404)
        size = min(max(size, 100), 2000)
        with Image.open(p) as im:
            im.draft("RGB", (size, size))
            img = ImageOps.exif_transpose(im).convert("RGB")
        img.thumbnail((size, size))
        buf = BytesIO()
        img.save(buf, "JPEG", quality=85)
        return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})

    print(f"Open {URL} in the browser. Ctrl+C to stop.", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")


def book_format(v):
    try:
        layout.page_size(v)
    except ValueError:
        raise argparse.ArgumentTypeError(f"use one of {', '.join(layout.FORMATS)} or WIDTHxHEIGHT in mm, like 210x280")
    return v


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="score, pick and lay the book out")
    m.add_argument("album", help="the iCloud album name")
    m.add_argument("--format", type=book_format, default="square-30", help="page size: " + ", ".join(layout.FORMATS) + " or WxH in mm")
    m.add_argument("--style", choices=list(layout.STYLES), default="pocket")
    m.add_argument("--spreads", type=int, help="fixed number of spreads (a spread is two pages); default 10 to 40")
    r = sub.add_parser("release", help="render one JPEG per spread and book.pdf")
    r.add_argument("album")
    sub.add_parser("review", help="review page in the browser")
    args = ap.parse_args()
    {"make": make, "release": release, "review": review}[args.cmd](args)
