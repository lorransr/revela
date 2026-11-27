#!/usr/bin/env python3
"""Escolhe as fotos do livro sem tirar nenhuma da máquina.

  revela dupes   agrupa fotos quase iguais e sugere a melhor de cada grupo
  revela picker  escolha no navegador e preview do livro em http://127.0.0.1:8765
  revela apply   monta data/selected com as escolhas e sincroniza o livro
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import threading
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, ImageFilter, ImageOps, ImageStat

DATA = Path("/data")
PHOTOS = DATA / "photos"
SELECTED = DATA / "selected"
PICKS = DATA / "picks.json"
BOOK = DATA / "books" / os.environ.get("BOOK", "livro")
EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
LAPLACE = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128)


def photos():
    # O icloudpd grava a data da foto no mtime, e o sync preserva esse mtime.
    files = [p for p in PHOTOS.rglob("*") if p.suffix.lower() in EXTS and not p.name.startswith(".")]
    return sorted(files, key=lambda p: (p.stat().st_mtime, str(p)))


def pid(p):
    return str(p.relative_to(PHOTOS))


def load_picks():
    return json.loads(PICKS.read_text()) if PICKS.exists() else {}


def save_picks(picks):
    tmp = PICKS.with_suffix(".tmp")
    tmp.write_text(json.dumps(picks, indent=1, ensure_ascii=False))
    tmp.replace(PICKS)


def measure(path):
    with Image.open(path) as im:
        im.draft("L", (1024, 1024))  # JPEG decodifica já reduzido: muito mais rápido
        g = im.convert("L")
    g.thumbnail((1024, 1024))
    h = g.resize((9, 8)).tobytes()
    hist = g.histogram()
    return {
        "hash": sum(1 << i for i in range(64) if h[i + i // 8] > h[i + i // 8 + 1]),
        "sharp": ImageStat.Stat(g.filter(LAPLACE)).var[0],
        "clipped": (sum(hist[:8]) + sum(hist[248:])) / sum(hist),
        "mean": ImageStat.Stat(g).mean[0],
    }


def dupes(a):
    items = []
    for n, p in enumerate(photos(), 1):
        items.append({"id": pid(p), "t": p.stat().st_mtime, **measure(p)})
        if n % 100 == 0:
            print(f"{n} fotos medidas", file=sys.stderr)
    if not items:
        sys.exit("Nenhuma foto em data/photos. Rode o sync primeiro.")

    groups = []
    for prev, it in zip([None] + items, items):
        similar = prev and it["t"] - prev["t"] <= a.seconds and bin(it["hash"] ^ prev["hash"]).count("1") <= a.distance
        if similar:
            groups[-1].append(it)
        else:
            groups.append([it])

    med = statistics.median(i["sharp"] for i in items) or 1
    picks = load_picks()

    def suggest(it, pick, why=""):
        if picks.get(it["id"], {}).get("by") != "voce":
            picks[it["id"]] = {"pick": pick, "by": "auto", "why": why}

    for g in groups:
        g.sort(key=lambda i: i["sharp"] * (1 - i["clipped"]), reverse=True)
        best, rest = g[0], g[1:]
        for it in rest:
            suggest(it, "out", f"parecida com {best['id']}, menos nítida")
        if best["mean"] < a.dark:  # antes da nitidez: foto escura também tem pouco contraste
            suggest(best, "out", "escura")
        elif best["sharp"] < a.blur * med:
            suggest(best, "out", "tremida ou fora de foco")
        else:
            suggest(best, "in")
        if rest:
            print(f"grupo de {len(g)}: " + ", ".join(f"{i['id']} ({i['sharp'] / med:.2f}x)" for i in g))
    save_picks(picks)
    out = sum(picks[i["id"]]["pick"] == "out" for i in items)
    print(f"\n{len(items)} fotos, {sum(len(g) > 1 for g in groups)} grupos de parecidas, "
          f"{out} fora. Nitidez em múltiplos da mediana do álbum; a primeira de cada grupo fica.")


def apply(a):
    picks = load_picks()
    keep = {pid(p): p for p in photos() if picks.get(pid(p), {}).get("pick") != "out"}
    for f in sorted(SELECTED.rglob("*"), reverse=True):
        if f.is_file() and str(f.relative_to(SELECTED)) not in keep:
            f.unlink()
        elif f.is_dir() and not any(f.iterdir()):
            f.rmdir()
    for i, p in keep.items():
        dst = SELECTED / i
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.link(p, dst)
    print(f"{len(keep)} fotos em data/selected")

    yaml = BOOK / f"{BOOK.name}.yaml"
    if not yaml.exists():
        print(f"O livro {BOOK.name} ainda não existe. Crie o livro e rode apply de novo.")
        return
    # ponytail: lê os ids com regex em vez de um parser YAML; troque por PyYAML se o fotobuch mudar o formato.
    in_book = re.findall(r"^\s*- id: ['\"]?(.+?)['\"]?$", yaml.read_text(), re.M)
    gone = [i for i in in_book if i not in keep]
    if gone:
        # O remove compara a regex com o caminho de origem, não com o id.
        subprocess.run(["fotobuch", "remove", *(f"^{re.escape('/photos/' + i)}$" for i in gone)], cwd=BOOK, check=True)
    subprocess.run(["fotobuch", "add", "-r", "/photos"], cwd=BOOK, check=True)


def picker(a):
    # Importa aqui: dupes e apply não precisam do servidor.
    import uvicorn
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import FileResponse, PlainTextResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    here = Path(__file__).resolve().parent
    templates = Jinja2Templates(here / "templates")
    lock = threading.Lock()
    app = FastAPI()
    # Bloqueia DNS rebinding: um site externo não consegue ler as fotos pelo navegador.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.mount("/static", StaticFiles(directory=here / "static"), name="static")

    def card(request, template, i, fora):
        picks = load_picks()
        items = [{"id": pid(p), **picks.get(pid(p), {})} for p in photos()]
        if fora:  # só as fotos que o dupes sugeriu tirar; "why" continua depois da sua escolha
            items = [x for x in items if x.get("why")]
        if i is None:
            i = next((k for k, x in enumerate(items) if x.get("by") != "voce"), len(items))
        i = max(0, min(i, len(items)))
        ctx = {"i": i, "n": len(items), "fora": fora, "p": items[i] if i < len(items) else None,
               "next": items[i + 1] if i + 1 < len(items) else None}
        return templates.TemplateResponse(request, template, ctx)

    @app.get("/")
    def index(request: Request, fora: bool = False):
        return card(request, "index.html", None, fora)

    @app.get("/card/{i}")
    def get_card(request: Request, i: int, fora: bool = False):
        return card(request, "card.html", i, fora)

    @app.post("/pick/{pick}/{photo:path}")
    def set_pick(request: Request, pick: Literal["in", "out"], photo: str, i: int, fora: bool = False):
        with lock:
            picks = load_picks()
            picks[photo] = {**picks.get(photo, {}), "pick": pick, "by": "voce"}
            save_picks(picks)
        return card(request, "card.html", i + 1, fora)

    @app.get("/img/{photo:path}")
    def image(photo: str):
        p = (PHOTOS / photo).resolve()
        if not p.is_relative_to(PHOTOS.resolve()) or not p.is_file():
            return Response(status_code=404)
        with Image.open(p) as im:
            im.draft("RGB", (1600, 1600))
            img = ImageOps.exif_transpose(im).convert("RGB")
        img.thumbnail((1600, 1600))
        buf = BytesIO()
        img.save(buf, "JPEG", quality=85)
        return Response(buf.getvalue(), media_type="image/jpeg")

    @app.get("/album")
    def album():
        pdf = BOOK / f"{BOOK.name}.pdf"
        if not pdf.exists():
            return PlainTextResponse("Sem preview. Rode fb build.", status_code=404)
        return FileResponse(pdf, media_type="application/pdf")

    print("Abra http://127.0.0.1:8765 no navegador. Ctrl+C para sair.", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dupes", help="agrupa fotos parecidas e sugere a melhor")
    d.add_argument("--seconds", type=float, default=10, help="intervalo máximo entre fotos do mesmo grupo")
    d.add_argument("--distance", type=int, default=12, help="diferença máxima de hash (0-64) entre fotos parecidas")
    d.add_argument("--blur", type=float, default=0.25, help="sai se a nitidez for menor que esta fração da mediana")
    d.add_argument("--dark", type=float, default=35, help="sai se o brilho médio (0-255) for menor que isto")
    sub.add_parser("picker", help="interface de escolha e preview do livro")
    sub.add_parser("apply", help="aplica as escolhas ao livro")
    args = ap.parse_args()
    {"dupes": dupes, "picker": picker, "apply": apply}[args.cmd](args)
