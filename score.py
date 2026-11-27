"""Scores each photo on this machine and writes only numbers: faces, smile, closed eyes, crying,
sharpness, brightness, aesthetics, and a CLIP vector that groups photos of the same scene."""
import sys

from PIL import Image, ImageFilter, ImageOps, ImageStat

_LAPLACE = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128)
# CLIP tells a cry from a funny face better than the face mesh. The first prompt is the one we test for.
_MOODS = ["a photo of a crying child", "a photo of a child making a funny face",
         "a photo of a smiling child", "a photo of a calm child"]


def _sharpness(gray, box=None):
    """Laplacian variance of the face, or of the sharpest block: a blurred background is not a blurred photo."""
    w, h = gray.size
    if box:
        crop = gray.crop((box[0] * w, box[1] * h, box[2] * w, box[3] * h))
        if min(crop.size) >= 32:
            return ImageStat.Stat(crop.filter(_LAPLACE)).var[0]
    blocks = [gray.crop((x * w // 4, y * h // 4, (x + 1) * w // 4, (y + 1) * h // 4)) for x in range(4) for y in range(4)]
    return max(ImageStat.Stat(b.filter(_LAPLACE)).var[0] for b in blocks)


class _Scorer:
    def __init__(self):
        import mediapipe as mp
        import open_clip
        import torch
        from mediapipe.tasks.python import BaseOptions, vision

        self.mp, self.torch = mp, torch
        self.faces = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path="/models/face_landmarker.task"),
            output_face_blendshapes=True, num_faces=8))
        self.clip, _, self.prep = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
        self.clip.eval()
        self.head = torch.nn.Linear(512, 1)
        self.head.load_state_dict(torch.load("/models/aesthetic.pth", map_location="cpu"))
        with torch.no_grad():
            t = self.clip.encode_text(open_clip.get_tokenizer("ViT-B-32")(_MOODS))
            self.moods = t / t.norm(dim=-1, keepdim=True)

    def __call__(self, path):
        import numpy as np

        with Image.open(path) as im:
            im.draft("RGB", (1024, 1024))  # JPEG decodes already reduced: much faster
            im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((1024, 1024))
        found = self.faces.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.asarray(im)))
        faces = []
        for marks, shapes in zip(found.face_landmarks, found.face_blendshapes):
            xs, ys = [m.x for m in marks], [m.y for m in marks]
            s = {c.category_name: c.score for c in shapes}
            faces.append({"box": [round(max(min(xs), 0), 3), round(max(min(ys), 0), 3),
                                  round(min(max(xs), 1), 3), round(min(max(ys), 1), 3)],
                          "smile": round((s["mouthSmileLeft"] + s["mouthSmileRight"]) / 2, 3),
                          "blink": round((s["eyeBlinkLeft"] + s["eyeBlinkRight"]) / 2, 3)})
        faces.sort(key=lambda f: (f["box"][2] - f["box"][0]) * (f["box"][3] - f["box"][1]), reverse=True)
        gray = im.convert("L")
        with self.torch.no_grad():
            e = self.clip.encode_image(self.prep(im).unsqueeze(0))
            e = e / e.norm(dim=-1, keepdim=True)
            aes = self.head(e).item()
            moods = (100 * e @ self.moods.T).softmax(dim=-1)[0].tolist()
        return {"w": im.width, "h": im.height, "faces": faces,
                "sharp": round(_sharpness(gray, faces[0]["box"] if faces else None), 1),
                "mean": round(ImageStat.Stat(gray).mean[0], 1),
                "aes": round(aes, 3), "cry": round(moods[0], 3),
                "emb": [round(v, 4) for v in e[0].tolist()]}


def score_all(paths, cache):
    """paths: {id: Path}. Adds the scores of the new or changed photos to cache: {id: scores}."""
    todo = {i: p for i, p in paths.items() if cache.get(i, {}).get("t") != p.stat().st_mtime}
    if todo:
        scorer = _Scorer()
        for n, (i, p) in enumerate(todo.items(), 1):
            cache[i] = {"t": p.stat().st_mtime, **scorer(p)}
            if n % 25 == 0 or n == len(todo):
                print(f"{n}/{len(todo)} photos scored", file=sys.stderr, flush=True)
        scorer.faces.close()
