# GitHub Pages sources

Static assets for https://moissanite-labs.github.io/abios/ (branch **`gh-pages`**, root deploy — settings unchanged).

Build committed HTML from templates:

```bash
python3 site/inject_version.py
```

Every CSS/PDF asset reference gets `?v=<git short sha>`.
