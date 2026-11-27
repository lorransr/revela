"""python3 test.py: the pick rules and the layout on fake data, no photos and no models."""
import random
from pathlib import Path

import layout
import pick


def photo(t, day="2024-07-13", sharp=1000, mean=120, aes=6.0, face=True, smile=0.5, blink=0.1, cry=0.1, emb=None):
    faces = [{"box": [0.4, 0.2, 0.6, 0.5], "smile": smile, "blink": blink}] if face else []
    return day, {"t": t, "w": 3, "h": 2, "faces": faces, "sharp": sharp, "mean": mean, "aes": aes, "cry": cry,
                 "emb": emb or [1.0 if k == t % 512 else 0.0 for k in range(512)]}


same = [1.0] + [0.0] * 511
raw = {
    "a": photo(0, emb=same, aes=6.0), "b": photo(10, emb=same, aes=7.0),  # one scene: b is better
    "dark": photo(1000, mean=10), "blur": photo(2000, sharp=10), "blink": photo(3000, blink=0.9),
    "cry": photo(4000, cry=0.9), "plain": photo(5000, face=False, aes=1.0),
    "fav": photo(6000, sharp=10), "extra": photo(6500, aes=5.5), "mine": photo(7000),
    "late": photo(8000, day="2024-07-14", aes=4.0),  # the weakest photo, but the only one of its day
}
scores = {f"{day}/{k}.jpg": s for k, (day, s) in raw.items()}
user = {"2024-07-13/mine.jpg": {"pick": "out", "by": "user", "why": ""}}


def run(spreads):
    p = pick.choose(scores, user, {"fav"}, 1, spreads)  # one photo a spread: spreads is the room in photos
    assert all(v["why"] for v in p.values() if v["pick"] == "out" and v["by"] == "auto"), "every cut has a reason"
    assert p["2024-07-13/mine.jpg"]["by"] == "user", "the user's pick wins"
    return {Path(i).stem: v for i, v in p.items()}


p = run(None)  # plenty of room: similar and plain photos come back, defects and the user's cut stay out
assert {k for k, v in p.items() if v["pick"] == "in"} == {"a", "b", "fav", "extra", "late", "plain"}, p
p = run(3)  # too many: cut the weakest, but keep every day; a favorite beats its defect
assert {k for k, v in p.items() if v["pick"] == "in"} == {"b", "fav", "late"}, p
p = run(4)  # one photo a scene: a stays out, though it beats extra
assert {k for k, v in p.items() if v["pick"] == "in"} == {"b", "fav", "extra", "late"}, p
p = run(5)  # too few: the best similar photo comes back first
assert {k for k, v in p.items() if v["pick"] == "in"} == {"a", "b", "fav", "extra", "late"}, p
assert [k for k, v in p.items() if v["hero"]] == ["b"], "the best of a day with 3 or more photos is the hero"
assert user["2024-07-13/mine.jpg"] == {"pick": "out", "by": "user", "why": ""}, "choose does not change its input"

random.seed(1)
fake = [{"id": f"2024-07-{13 + i // 12}/IMG_{i}.jpg", **random.choice([{"w": 3, "h": 2}, {"w": 2, "h": 3}]),
         "faces": [], "hero": i % 9 == 0} for i in range(60)]
heroes = {p["id"] for p in fake if p["hero"]}
order = [p["id"] for p in fake]
for style in layout.STYLES:
    book = layout.layout(fake, "square-30", style)
    (pw, ph), b = book["page"], book["bleed"]
    pats = [s["pattern"] for s in book["spreads"]]
    ids = [s["id"] for sp in book["spreads"] for s in sp["slots"]]
    assert sorted(ids) == sorted(order), "every photo once"
    assert all(abs(k - order.index(i)) <= 1 for k, i in enumerate(ids)), "a photo moves one place at most"
    assert all(x != y for x, y in zip(pats, pats[1:])), "no pattern twice in a row"
    calm = [n for n, pat in enumerate(pats) if "breath" in pat or "single" in pat]
    assert all(y - x >= 4 for x, y in zip(calm, calm[1:])), f"a breathing page every few spreads: {pats}"
    for sp in book["spreads"]:
        pages = sp["pattern"].split("|")
        for s in sp["slots"]:
            assert -b - 1e-6 <= s["x"] and s["x"] + s["w"] <= 2 * pw + b + 1e-6, s
            if style == "pocket" and pages != ["pano"]:
                assert s["x"] >= pw - 1e-6 or s["x"] + s["w"] <= pw + 1e-6, f"crosses the fold: {sp['pattern']}"
            if s["id"] in heroes:
                page = pages[0] if pages == ["pano"] or s["x"] < pw else pages[1]
                assert page in ("full", "large", "pano"), f"a hero on a {page} page"
    print(style, len(pats), "spreads:", " ".join(pats))
print("ok")
