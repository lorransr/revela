# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

- App: the review page is a FastAPI + Jinja2 template (`templates/review.html`), served on `127.0.0.1` only.
- Landing page: static HTML/CSS in `docs/`, for GitHub Pages. No framework. English by default, Portuguese when the browser asks for `pt`.

## Users

Families who want to print their photos as a book, safely and simply: weddings, babies, photo shoots, trips, memories. Their photos live in an iCloud album. Today the person who runs revela is technical enough to run Docker and a coding agent; the person who enjoys the book is the whole family.

## Product Purpose

revela turns an iCloud album into a layflat photobook ready for print, and no photo leaves the computer. Success: the family holds a printed book of their own photos without uploading them to a photobook site.

## Positioning

The photos never leave the machine. The download talks only to Apple, the scoring and the layout run without network, and the review page listens only on `127.0.0.1`. An agent or one command does the work: it picks the photos, drops duplicates, blurry and crying-face shots, and lays them out like a professional album.

## Operating Context

1. Ask an agent for a book from an album, or run `./revela make "<album>"`.
2. Open the review page, remove or add photos, press "Rebuild book".
3. Change the book in words ("fewer photos", "scrapbook style"); the scores are cached, so a rebuild takes seconds.
4. `./revela release` writes one JPEG per spread and `book.pdf`, 300 DPI, 3 mm bleed, for a print shop.

## Capabilities and Constraints

- Formats: `square-20`, `square-25`, `square-30`, `landscape-a4`, `portrait-20x25`, or `WIDTHxHEIGHT` in mm. Styles: `pocket` (default) and `scrapbook`. The default format is `square-30`.
- A heart in the iPhone Photos app keeps a photo. A user choice on the review page is never overwritten.
- revela makes no cover: the cover is linen without a photo. The binding is layflat.
- revela does not print or sell books. The user takes the PDF to a print shop.
- Undecided: a hosted or no-terminal version does not exist.

## Brand Commitments

- Name: revela (Portuguese for "develops", as in developing film). Lowercase.
- The review page loads nothing from outside. The landing page keeps the same promise: self-hosted fonts and images.

## Evidence on Hand

- Real product facts: README.md, CONTRIBUTING.md.
- No testimonials, users, press, or printed-book photos. Do not invent them.
- The photos in `data/` are private (a child). Never use or open them. Landing imagery comes from free stock photo libraries on the themes above, credited.

## Product Principles

1. Privacy is the product, not a feature: every surface proves it, none only claims it.
2. The book is the hero. The interface steps back so the photos lead.
3. The user's choice wins over the machine's choice.
4. Simple for the family, honest about the terminal it needs today.
