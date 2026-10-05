# Metal Gear Solid (1998) — Unofficial Fan Overview

A small, static fan site covering the original PlayStation stealth game.

## Contents

- `index.html` — single-page overview with introduction, mission, characters, stealth gameplay, and legacy.
- `styles.css` — dark-green Codec-inspired styling with responsive layout.
- `tests/test_site.py` — compact unittest suite (12 checks).

## Local Serving

```bash
python -m http.server --directory .
```

Then open http://127.0.0.1:8000 in your browser.

## Validation

```bash
python -B -m unittest discover -s tests -v
```

All checks run in-process (no server, no subprocess).
