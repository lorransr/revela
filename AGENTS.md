# revela

Never open photos or PDFs in `data/`. Whatever you read goes to the model provider, and the photos are of a child. Work only with the text output of the commands.

When the user asks for a book from an iCloud album:

1. Run `./revela make "<album>"`. Add `--format`, `--style` or `--spreads` only when the user asks, for example "a 20x20 book" is `--format square-20`.
2. If the sync stops at the Apple login, ask the user to run `./revela login` in a terminal (in Claude Code: `! ./revela login`), then run `make` again.
3. Give the user the summary and the review link. On that page the user removes and adds photos, then presses "Rebuild book".
4. For a change in words, such as "fewer photos" or "the scrapbook style", run `make` again with new options. The scores are cached, so this takes seconds.
5. When the user approves the book, run `./revela release "<album>"` and give the path of the PDF.

Never change a pick with `"by": "user"` in `picks.json`. Those are the user's choices.
