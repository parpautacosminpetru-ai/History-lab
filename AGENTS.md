# Working in this repository

The existing Android/JavaScript application at `app/` is maintained independently.
HUI lives in `hui/`. Do not replace the existing app, data format, or workflows.

For HUI changes:
- Keep Reader independent of the Python Indexer and every AI provider.
- Source text and original files are immutable. Use stand-off annotations.
- Offsets count Unicode code points; ranges are half-open `[start, end)`.
- Never treat coordinate validation as semantic or historical verification.
- Run `python -m pytest hui/indexer/tests` and `npm test` before delivery.
- Record actual platform/build results; do not claim unexecuted builds passed.
- Do not commit researchers' PDFs, API keys, local databases, or exported packages.
