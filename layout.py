"""Lays the picked photos out on spreads and renders the book.

The book is a list of spreads. Each spread is two pages, or one panorama across the fold.
A greedy pass picks the cheapest spread for the next photos. The cost keeps the rhythm:
no pattern twice in a row, a calm spread after a busy one, a breathing page now and then.
"""
import itertools
from pathlib import Path

from PIL import Image, ImageOps

FORMATS = {"square-20": (200, 200), "square-25": (250, 250), "square-30": (300, 300),
           "landscape-a4": (297, 210), "portrait-20x25": (200, 250)}
BLEED = 3
MAX_CROP = 0.4  # a photo in a cover slot loses at most this share of its width or height


def page_size(fmt):
    if fmt in FORMATS:
        return FORMATS[fmt]
    w, h = fmt.lower().split("x")  # a free format: "210x280", in mm
    return float(w), float(h)


def grid(rows, cols, pw, ph, margin, gap, scale=1.0):
    iw, ih = (pw - 2 * margin) * scale, (ph - 2 * margin) * scale
    x0, y0 = (pw - iw) / 2, (ph - ih) / 2
    cw, ch = (iw - (cols - 1) * gap) / cols, (ih - (rows - 1) * gap) / rows
    return [(x0 + c * (cw + gap), y0 + r * (ch + gap), cw, ch) for r in range(rows) for c in range(cols)]


def pages(style, pw, ph):
    """Page types of a style: name -> (cells, fill, hero). A hero photo only goes on a hero page."""
    if style == "pocket":
        g = 3
        return {
            "full": (grid(1, 1, pw, ph, 0, g), "cover", True),
            "stack": (grid(2, 1, pw, ph, 0, g), "cover", False),
            "side": (grid(1, 2, pw, ph, 0, g), "cover", False),
            "breath": (grid(1, 1, pw, ph, 0.14 * min(pw, ph), g), "contain", False),
            "duo": (grid(1, 2, pw, ph, 0.1 * min(pw, ph), 2 * g), "contain", False),  # takes a portrait and a landscape
        }
    m, g = 20, 10
    big, = grid(1, 2, pw, ph, m, g)[:1]
    right = grid(2, 2, pw, ph, m, g)
    return {
        "large": (grid(1, 1, pw, ph, m, g), "contain", True),
        "single": (grid(1, 1, pw, ph, m, g, 0.7), "contain", False),
        "stack": (grid(2, 1, pw, ph, m, g), "contain", False),
        "side": (grid(1, 2, pw, ph, m, g), "contain", False),
        "trio": ([big, right[1], right[3]], "contain", False),
        "grid": (right, "contain", False),
    }


STYLES = {
    "pocket": {"paper": "#ffffff", "per_spread": 2.6, "pano": True},
    "scrapbook": {"paper": "#f3ede2", "per_spread": 5.0, "pano": False},
}


def loss(p, cw, ch):
    r = (p["w"] / p["h"]) / (cw / ch)
    return 1 - min(r, 1 / r)


def crop(p, cw, ch):
    """Cover crop that keeps the faces: the union of faces if it fits, else the largest face."""
    a, c = p["w"] / p["h"], cw / ch
    faces = p.get("faces") or []
    target = None
    if faces:
        union = [min(f[0] for f in faces), min(f[1] for f in faces), max(f[2] for f in faces), max(f[3] for f in faces)]
        largest = max(faces, key=lambda f: (f[2] - f[0]) * (f[3] - f[1]))
        target = union
    clamp = lambda v, size: min(max(v, 0.0), 1.0 - size)
    if a > c:  # wider than the slot: cut the sides
        w = c / a
        if target and target[2] - target[0] > w:
            target = largest
        x = (target[0] + target[2]) / 2 - w / 2 if target else 0.5 - w / 2
        x = clamp(x, w)
        return [x, 0.0, x + w, 1.0]
    h = a / c  # taller than the slot: cut top and bottom, faces in the upper third
    if target and target[3] - target[1] > h:
        target = largest
    y = (target[1] + target[3]) / 2 - h / 3 if target else 0.45 - h / 2
    y = clamp(y, h)
    return [0.0, y, 1.0, y + h]


def place(photos, cells, fill, dx, pw, ph, outer_left, outer_right):
    """Slots in spread coordinates. Cover cells on a page edge run into the bleed; the fold gets no bleed."""
    slots, cost = [], 0.0
    for p, (x, y, w, h) in zip(photos, cells):
        x += dx
        if fill == "cover":
            lost = loss(p, w, h)
            if lost > MAX_CROP:
                return None, None
            cost += lost
            x0, y0, x1, y1 = x, y, x + w, y + h
            if outer_left and x0 <= dx + 1e-6:
                x0 -= BLEED
            if outer_right and x1 >= dx + pw - 1e-6:
                x1 += BLEED
            y0 -= BLEED if y0 <= 1e-6 else 0
            y1 += BLEED if y1 >= ph - 1e-6 else 0
            slots.append({"id": p["id"], "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
                          "crop": crop(p, x1 - x0, y1 - y0)})
        else:
            a = p["w"] / p["h"]
            fw, fh = (w, w / a) if a > w / h else (h * a, h)
            cost += 0.5 * loss(p, w, h)
            slots.append({"id": p["id"], "x": x + (w - fw) / 2, "y": y + (h - fh) / 2, "w": fw, "h": fh,
                          "crop": [0.0, 0.0, 1.0, 1.0]})
    return slots, cost


def candidates(style, pw, ph):
    """Spread patterns: every pair of page types, plus the panorama."""
    types = pages(style, pw, ph)
    out = [((l, r), [(types[l], 0, True, False), (types[r], pw, False, True)])
           for l, r in itertools.product(types, repeat=2)]
    out += [((l, None), [(types[l], 0, True, False)]) for l in types]  # the last spread may end on a blank page
    if STYLES[style]["pano"]:
        out.append((("pano",), [((grid(1, 1, 2 * pw, ph, 0, 0), "cover", True), 0, True, True)]))
    return out


def pair(photos):
    """Swap two neighbours of the same day when that puts two photos of the same orientation together.

    A photo moves one place at most, so the story keeps its order.
    """
    ps = list(photos)
    land = lambda p: p["w"] > p["h"]
    day = lambda p: p["id"].split("/")[0]
    k = 0
    while k + 2 < len(ps):
        a, b, c = ps[k:k + 3]
        if land(a) != land(b) and land(a) == land(c) and day(b) == day(c) and not b.get("hero") and not c.get("hero"):
            ps[k + 1], ps[k + 2] = c, b
            k += 2
        else:
            k += 1
    return ps


def layout(photos, fmt="square-30", style="pocket"):
    """photos: dicts with id, w, h (as displayed), faces (normalized boxes), hero. In book order."""
    pw, ph = page_size(fmt)
    st = STYLES[style]
    cands = candidates(style, pw, ph)
    photos = pair(photos)

    def options(i, hist, placed, last_breath):
        """Every spread that fits the photos from i on, with its cost. hist: (pattern, photo count) of past spreads."""
        out = []
        prev, prev_n = hist[-1] if hist else (None, 0)
        prev2 = hist[-2][0] if len(hist) > 1 else None
        for pattern, parts in cands:
            n = sum(len(cells) for (cells, _, _), *_ in parts)
            group = photos[i:i + n]
            if len(group) < n or (pattern[-1] is None and i + n < len(photos)):
                continue
            calm = [t for t in pattern if t in ("breath", "single")]
            if calm and (len(calm) > 1 or len(hist) - last_breath < 4):
                continue  # one breathing page every few spreads, never two side by side
            slots, cost, k = [], 0.0, 0
            for (cells, fill, hero_ok), dx, ol, orr in parts:
                ps = group[k:k + len(cells)]
                k += len(cells)
                if any(p.get("hero") for p in ps) and not hero_ok:
                    break
                if pattern == ("pano",) and not ps[0].get("hero"):
                    break  # the panorama is only for heroes
                sl, c = place(ps, cells, fill, dx, 2 * pw if pattern == ("pano",) else pw, ph, ol, orr)
                if sl is None:
                    break
                slots += sl
                cost += c
            else:
                cost += 10 if pattern == prev else 0
                cost += 1.5 if pattern == prev2 else 0
                cost += 0.4 * len(set(pattern) & set(prev or ()))  # pages that repeat the last spread
                cost += 2 if prev_n >= 3 and n >= 3 else 0  # a calm spread after a busy one
                cost += 0.5 if calm else 0
                cost += 0.4 * pattern.count("duo")  # the pocket style is mostly full bleed
                cost += 1.2 * abs(placed + n - st["per_spread"] * (len(hist) + 1)) / st["per_spread"]
                cost += 0.8 if len({p["id"].split("/")[0] for p in group}) > 1 else 0
                cost -= 2 if pattern == ("pano",) else 0
                out.append((cost, pattern, slots, n))
        return out

    spreads, hist, i, placed, last_breath = [], [], 0, 0, -9
    while i < len(photos):
        best = None
        for cost, pattern, slots, n in options(i, hist, placed, last_breath):
            # Look one spread ahead: a cheap spread now must not leave only a bad one next.
            lb = len(hist) if "breath" in pattern or "single" in pattern else last_breath
            nxt = options(i + n, hist + [(pattern, n)], placed + n, lb) if i + n < len(photos) else [(0,)]
            total = cost + (min(o[0] for o in nxt) if nxt else 20)
            if best is None or total < best[0]:
                best = (total, pattern, slots, n)
        if best is None:
            # A hero too tall or too wide for any cover slot: it goes in as a normal photo.
            assert photos[i].get("hero"), f"no spread fits {photos[i]['id']}"
            photos[i] = {**photos[i], "hero": False}
            continue
        _, pattern, slots, n = best
        if "breath" in pattern or "single" in pattern:
            last_breath = len(hist)
        hist.append((pattern, n))
        spreads.append({"pattern": "|".join(t or "blank" for t in pattern), "slots": slots})
        i += n
        placed += n
    return {"page": [pw, ph], "bleed": BLEED, "paper": st["paper"], "style": style, "format": fmt, "spreads": spreads}


def render(book, photos_dir, out_dir, dpi=300):
    """One JPEG per spread, with bleed, and book.pdf with all of them."""
    import img2pdf

    pw, ph = book["page"]
    b = book["bleed"]
    px = lambda mm: round(mm / 25.4 * dpi)
    W, H = px(2 * pw + 2 * b), px(ph + 2 * b)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("spread-*.jpg"):
        old.unlink()
    files = []
    for n, sp in enumerate(book["spreads"], 1):
        canvas = Image.new("RGB", (W, H), book["paper"])
        for s in sp["slots"]:
            x0, y0 = px(s["x"] + b), px(s["y"] + b)
            x1, y1 = px(s["x"] + s["w"] + b), px(s["y"] + s["h"] + b)
            cx0, cy0, cx1, cy1 = s["crop"]
            need = round(max((x1 - x0) / (cx1 - cx0), (y1 - y0) / (cy1 - cy0)))
            with Image.open(photos_dir / s["id"]) as im:
                im.draft("RGB", (need, need))  # JPEG decodes already reduced, but never below what the slot needs
                im = ImageOps.exif_transpose(im).convert("RGB")
            box = (cx0 * im.width, cy0 * im.height, cx1 * im.width, cy1 * im.height)
            canvas.paste(im.resize((x1 - x0, y1 - y0), Image.LANCZOS, box=box), (x0, y0))
        f = out_dir / f"spread-{n:02}.jpg"
        canvas.save(f, quality=92, dpi=(dpi, dpi))
        files.append(str(f))
    pdf = out_dir / "book.pdf"
    pdf.write_bytes(img2pdf.convert(files, layout_fun=img2pdf.get_fixed_dpi_layout_fun((dpi, dpi))))
    return pdf


if __name__ == "__main__":
    # Self-check without photos: rhythm and geometry on fake photos.
    import random

    random.seed(1)
    fake = [{"id": f"2024-07-{13 + i // 12}/IMG_{i}.jpg", **random.choice([{"w": 3, "h": 2}, {"w": 2, "h": 3}]),
             "faces": [], "hero": i % 9 == 0} for i in range(60)]
    for style in STYLES:
        book = layout(fake, "square-30", style)
        pats = [s["pattern"] for s in book["spreads"]]
        ids = [s["id"] for sp in book["spreads"] for s in sp["slots"]]
        order = [p["id"] for p in fake]
        assert sorted(ids) == sorted(order), "every photo once"
        assert all(abs(k - order.index(i)) <= 1 for k, i in enumerate(ids)), "a photo moves one place at most"
        assert all(a != b for a, b in zip(pats, pats[1:])), "no pattern twice in a row"
        for sp in book["spreads"]:
            for s in sp["slots"]:
                assert -BLEED - 1e-6 <= s["x"] and s["x"] + s["w"] <= 600 + BLEED + 1e-6, s
                if style == "pocket" and sp["pattern"] != "pano" and s["w"] < 600:
                    assert s["x"] >= 300 - 1e-6 or s["x"] + s["w"] <= 300 + 1e-6, f"crosses the fold: {sp['pattern']}"
        assert len(set(pats)) >= 6, f"too few patterns: {set(pats)}"
        print(style, len(pats), "spreads:", " ".join(pats))
