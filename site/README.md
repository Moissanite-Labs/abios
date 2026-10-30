# GitHub Pages sources

Static assets for https://moissanite-labs.github.io/abios/ (branch **`gh-pages`**, root deploy).

## Build (required before publish)

From the repository root:

```bash
python3 site/inject_version.py
```

This writes committed HTML from `*.template.html` and stamps `?v=<git short sha>` on CSS links.

## Publish to `gh-pages` (do not copy the whole `site/` tree)

Deploy **only** these built artifacts (plus anything `inject_version.py` emits alongside them):

- `index.html`
- `abios.html`
- `paper.html`
- `reproduce.html`
- `spec-abios-3.html`
- `404.html`
- `favicon.svg`
- `og-image.png`
- `styles-abios.css`

Do **not** publish `*.template.html`, `inject_version.py`, or stale `abios.pdf` (use `paper.html` generated from `paper/abios.md`).

Example:

```bash
python3 site/inject_version.py
rsync -av --include='*.html' --include='*.css' --include='*.svg' --include='*.png' --exclude='*' site/ /path/to/gh-pages-checkout/
```
