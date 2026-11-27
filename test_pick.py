"""python3 test_pick.py: the pick rules on fake scores, no photos and no models."""
import json
import tempfile
from pathlib import Path

import revela


def photo(t, day="2024-07-13", sharp=1000, mean=120, aes=6.0, face=True, smile=0.5, blink=0.1, cry=0.1, emb=None):
    faces = [{"box": [0.4, 0.2, 0.6, 0.5], "smile": smile, "blink": blink}] if face else []
    return day, {"t": t, "w": 3, "h": 2, "faces": faces, "sharp": sharp, "mean": mean, "aes": aes, "cry": cry,
                 "emb": emb or [1.0 if k == t % 512 else 0.0 for k in range(512)]}


with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    same = [1.0] + [0.0] * 511
    raw = {
        "a": photo(0, emb=same, aes=5.0), "b": photo(10, emb=same, aes=7.0),  # one scene: b is better
        "dark": photo(1000, mean=10), "blur": photo(2000, sharp=10), "blink": photo(3000, blink=0.9),
        "cry": photo(4000, cry=0.9), "plain": photo(5000, face=False, aes=1.0),
        "fav": photo(6000, sharp=10), "extra": photo(6500, aes=5.5), "mine": photo(7000), "late": photo(8000, day="2024-07-14"),
    }
    scores = {f"{day}/{k}.jpg": s for k, (day, s) in raw.items()}
    (d / "favorites.txt").write_text("fav\n")
    (d / "picks.json").write_text(json.dumps({"2024-07-13/mine.jpg": {"pick": "out", "by": "user", "why": ""}}))

    def run(spreads):
        revela.pick(d, scores, "pocket", spreads)
        return {Path(i).stem: v for i, v in json.loads((d / "picks.json").read_text()).items()}

    p = run(1)  # one spread: room for 3 photos
    assert p["a"]["why"] == "similar to b", p["a"]
    for k, why in [("dark", "too dark"), ("blur", "blurry"), ("blink", "eyes closed"), ("cry", "crying"),
                   ("plain", "no people, not striking"), ("extra", "cut to fit 1 spreads")]:
        assert (p[k]["pick"], p[k]["why"]) == ("out", why), (k, p[k])
    assert p["fav"] == {"pick": "in", "by": "user", "why": "favorite", "hero": False}, "a favorite beats a defect"
    assert p["mine"]["pick"] == "out" and p["mine"]["by"] == "user", "the user's pick wins"
    assert {k for k, v in p.items() if v["pick"] == "in"} == {"b", "fav", "late"}, "cut the weakest, keep every day"

    p = run(2)  # two spreads: room for 5 photos, so the best similar one comes back
    assert {k for k, v in p.items() if v["pick"] == "in"} == {"a", "b", "fav", "extra", "late"}, p
    assert [k for k, v in p.items() if v["hero"]] == ["b"], "the best of a day with 3 or more photos is the hero"
print("ok")
