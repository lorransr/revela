"""Which photos go in the book. The rules read only scores, so they run without photos or models."""
import statistics
from collections import Counter
from pathlib import Path


def choose(scores, picks, favorites, per_spread, spreads=None):
    """scores: {id: scores} in book order. picks: the last picks.json. favorites: file stems with a heart.

    Returns the new picks.json. The user's picks and the favorites always win.
    """
    picks = {i: dict(p) for i, p in picks.items()}
    for i in scores:
        if Path(i).stem in favorites and picks.get(i, {}).get("by") != "user":
            picks[i] = {"pick": "in", "by": "user", "why": "favorite"}
    user = {i for i in scores if picks.get(i, {}).get("by") == "user"}
    ids = list(scores)
    day = lambda i: i.split("/")[0]
    med = statistics.median(s["sharp"] for s in scores.values()) or 1

    def defect(s):
        if s["mean"] < 35:  # before sharpness: a dark photo also has little contrast
            return "too dark"
        if s["sharp"] < 0.25 * med:
            return "blurry"
        if s["faces"] and s["faces"][0]["blink"] > 0.5:
            return "eyes closed"
        # ponytail: CLIP prompt, not calibrated; tune the threshold with real albums.
        if s["faces"] and s["cry"] > 0.5:
            return "crying"
        return None

    q = {i: s["aes"] + (s["faces"][0]["smile"] + 0.5 if s["faces"] else 0) for i, s in scores.items()}
    scenes = []
    for prev, i in zip([None] + ids, ids):
        a, b = scores[i], scores.get(prev)
        if b and a["t"] - b["t"] <= 120 and sum(x * y for x, y in zip(a["emb"], b["emb"])) >= 0.9:
            scenes[-1].append(i)
        else:
            scenes.append([i])
    auto = {}
    for scene in scenes:
        ok = [i for i in scene if not defect(scores[i])]
        best = max(ok, key=q.get) if ok else None
        for i in scene:
            why = defect(scores[i])
            auto[i] = ("out", why) if why else ("in", "") if i == best else ("out", f"similar to {Path(best).stem}")
    plain = statistics.quantiles([s["aes"] for s in scores.values()], n=4)[2] if len(scores) > 1 else 0
    for i, (p, _) in auto.items():
        if p == "in" and not scores[i]["faces"] and scores[i]["aes"] < plain:
            auto[i] = ("out", "no people, not striking")

    final = {i: (picks[i]["pick"], picks[i]["why"]) if i in user else auto[i] for i in ids}
    lo, hi = (spreads, spreads) if spreads else (10, 40)
    lo_n, hi_n = round(lo * per_spread), round(hi * per_spread)
    kept = [i for i in ids if final[i][0] == "in"]
    if len(kept) > hi_n:  # too many: cut the weakest auto picks, but keep every day in the book
        days = Counter(map(day, kept))
        for i in sorted((i for i in kept if i not in user), key=q.get):
            if len(kept) <= hi_n:
                break
            if days[day(i)] > 1:
                days[day(i)] -= 1
                kept.remove(i)
                final[i] = ("out", f"cut to fit {hi} spreads")
    if len(kept) < lo_n:  # too few: bring back the best of the similar and plain ones
        back = [i for i in ids if final[i][0] == "out" and i not in user
                and final[i][1].startswith(("similar", "no people"))]
        for i in sorted(back, key=q.get, reverse=True)[:lo_n - len(kept)]:
            final[i] = ("in", "")
        kept = [i for i in ids if final[i][0] == "in"]

    # One hero about every 4 spreads, the best photo of its stretch, and at least one per day.
    heroes, chunk = set(), max(3, round(4 * per_spread))
    for d in dict.fromkeys(map(day, kept)):
        run = [i for i in kept if day(i) == d]
        for k in range(0, len(run), chunk):
            part = run[k:k + chunk]
            if len(part) >= 3:
                heroes.add(max(part, key=lambda i: (bool(scores[i]["faces"]), q[i])))

    for i in ids:
        if i not in user:
            picks[i] = {"pick": final[i][0], "by": "auto", "why": final[i][1]}
        picks[i]["hero"] = i in heroes
    return picks
