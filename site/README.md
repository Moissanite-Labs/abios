# GitHub Pages source (`site/`)

Static assets for https://aska-digital.github.io/protean-sym2p/ (branch **`gh-pages`**, root deploy — settings unchanged).

## Build

```bash
python3 site/inject_version.py
```

Writes `*.html` from `*.template.html` and stamps `?v=<git short sha>` on local CSS/asset links.

## Publish to `gh-pages`

After merging to `main`, sync (maintainer):

```bash
git checkout gh-pages
cp site/index.html site/sym3.html site/spec-v3.html site/paper.html site/reproduce.html \
   site/styles-sym3.css site/404.html site/favicon.svg site/og-image.png site/sym3.pdf .
git add -A && git commit -m "Sync site from main" && git push origin gh-pages
git checkout main
```

Copy `paper/sym3.pdf` into `site/sym3.pdf` before sync when the PDF is rebuilt.
