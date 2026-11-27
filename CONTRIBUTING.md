# Contributing

## Code design

- Each module is deep: a small interface that hides much logic. Names that start with `_` are internal, and no other module uses them.
  - `pick.py`: `choose` decides which photos go in the book.
  - `layout.py`: `layout` puts the picks on spreads, `render` writes the JPEGs and the PDF.
  - `score.py`: `score_all` scores the photos with the models in the image.
  - `color.py`: `open_srgb` decodes photos in the color space shared by print and review.
  - `revela.py`: the command line, the review server and the album files. It is the only module that reads or writes `data/`.
- The rules are pure functions: data in, data out. They do not read files, so a test needs no disk, no photos and no models.
- One rule lives in one place. Another module or a script calls it, for example `sync.sh` calls `revela.slug`.
- Do not change the behavior in a refactor. A refactor of the pick or the layout keeps `picks.json` and `book.json` of the same album the same, byte for byte.
- Mark a deliberate shortcut with a `ponytail:` comment that names its limit.

## Tests

`python3 test.py` runs on the host, without Docker. The host needs only Pillow.

The print and review color regression uses generated images, no real photos or models:

```sh
uv run --no-project --with img2pdf --with pikepdf --with fastapi --with uvicorn --with jinja2 python -m unittest test_color
```

- A test calls only the interface of a module.
- A test checks a behavior, not the implementation. Do not compare a string or a dict that you copied from the code.
- A test must fail when its rule breaks. Break the rule on purpose once, for example with `sed`, and see the test fail.

## Product decisions

- The layout follows a professional album: a rhythm, no spread equal to the one before, a calm spread after a busy one, a breathing page now and then, and heroes.
- The cover is linen without a photo, so revela does not make a cover. The binding is layflat.
- A funny face stays in the book. A crying face goes out. A heart in the iPhone Photos app keeps a photo.
