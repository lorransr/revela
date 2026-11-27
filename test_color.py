"""Integration tests for color in print files and the review image route.

Run with the runtime dependencies installed: python3 -m unittest test_color
"""
import base64
import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pikepdf
from PIL import Image, ImageCms

import layout

# Compact-ICC-Profiles AdobeCompat-v2.icc, CC0: https://github.com/saucecontrol/Compact-ICC-Profiles
ADOBE_RGB = base64.b64decode(
    "AAABdkFEQkUCEAAAbW50clJHQiBYWVogB+IAAwAUAAkADgAdYWNzcE1TRlQAAAAAc2F3c2N0cmwAAAAAAAAAAAAAAAAAAPbWAAEAAAAA0y1oYW5kXsIZ29tUzMjeAr7E6+G1DAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJZGVzYwAAAPAAAABfY3BydAAAAQwAAAAMd3RwdAAAARgAAAAUclhZWgAAASwAAAAUZ1hZWgAAAUAAAAAUYlhZWgAAAVQAAAAUclRSQwAAAWgAAAAOZ1RSQwAAAWgAAAAOYlRSQwAAAWgAAAAOZGVzYwAAAAAAAAAFQTk4QwAAAAAAAAAAAAAAAHRleHQAAAAAQ0MwAFhZWiAAAAAAAADzUQABAAAAARbMWFlaIAAAAAAAAJwYAABPpQAABPxYWVogAAAAAAAANI0AAKAsAAAPlVhZWiAAAAAAAAAmMQAAEC8AAL6cY3VydgAAAAAAAAABAjM="
)


class ColorIntegration(unittest.TestCase):
    def assert_pixel(self, image, xy, expected):
        actual = image.getpixel(xy)
        self.assertTrue(all(abs(a - b) <= 4 for a, b in zip(actual, expected)), (actual, expected))

    def assert_srgb(self, profile):
        self.assertTrue(profile, "output must carry an sRGB profile")
        description = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(BytesIO(profile)))
        self.assertIn("srgb", description.lower())

    def test_print_and_review_preserve_color(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            album = root / "fixture"
            photos = album / "photos"
            photos.mkdir(parents=True)
            srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
            for name, profile in (("adobe.png", ADOBE_RGB), ("plain.png", None), ("srgb.png", srgb)):
                Image.new("RGB", (100, 100), (180, 100, 50)).save(photos / name, icc_profile=profile)

            book = {"page": [30, 20], "bleed": 0, "paper": "white", "spreads": [{"slots": [
                {"id": name, "x": x, "y": 0, "w": 20, "h": 20, "crop": [0, 0, 1, 1]}
                for x, name in ((0, "adobe.png"), (20, "plain.png"), (40, "srgb.png"))
            ]}]}
            (album / "book.json").write_text(json.dumps(book))
            pdf = layout.render(book, photos, album / "print", dpi=127)
            with Image.open(album / "print" / "spread-01.jpg") as spread:
                self.assert_srgb(spread.info.get("icc_profile"))
                self.assert_pixel(spread, (50, 50), (203, 100, 42))
                self.assert_pixel(spread, (150, 50), (180, 100, 50))
                self.assert_pixel(spread, (250, 50), (180, 100, 50))
            with pikepdf.open(pdf) as document:
                image = next(iter(document.pages[0].Resources.XObject.values()))
                self.assertEqual(str(image.ColorSpace[0]), "/ICCBased")
                self.assert_srgb(image.ColorSpace[1].read_bytes())

            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            server = subprocess.Popen([sys.executable, "-c", """
import sys
from pathlib import Path
import revela, uvicorn
revela.ALBUMS = Path(sys.argv[1])
run = uvicorn.run
uvicorn.run = lambda app, **kwargs: run(app, host="127.0.0.1", port=int(sys.argv[2]), log_level="error")
revela.review(None)
""", str(root), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                for attempt in range(100):
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/img/fixture/adobe.png?size=100", timeout=1) as response:
                            data = response.read()
                        break
                    except URLError:
                        if server.poll() is not None:
                            self.fail(server.stderr.read().decode())
                        time.sleep(.05)
                else:
                    self.fail("review server did not start")
                with Image.open(BytesIO(data)) as review:
                    self.assert_srgb(review.info.get("icc_profile"))
                    self.assert_pixel(review, (50, 50), (203, 100, 42))
                for name in ("plain.png", "srgb.png"):
                    with urlopen(f"http://127.0.0.1:{port}/img/fixture/{name}?size=100") as response:
                        with Image.open(BytesIO(response.read())) as review:
                            self.assert_srgb(review.info.get("icc_profile"))
                            self.assert_pixel(review, (50, 50), (180, 100, 50))
            finally:
                server.terminate()
                server.wait(timeout=5)
                server.stderr.close()


if __name__ == "__main__":
    unittest.main()
