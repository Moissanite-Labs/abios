#!/usr/bin/env python3
"""Build site/*.html from *.template.html with ?v=<git short sha> cache busters."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

SITE = Path(__file__).resolve().parent
SKIP_OUTPUT = {"gh-pages-index-original.html", "index-before.html"}


def git_short_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=7", "HEAD"],
            cwd=SITE.parent,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "dev"


def inject(html: str, sha: str) -> str:
    def css_repl(match: re.Match[str]) -> str:
        path = match.group(1)
        if "?v=" in match.group(0):
            return match.group(0)
        return f'href="{path}?v={sha}"'

    def src_repl(match: re.Match[str]) -> str:
        path = match.group(1)
        if "?v=" in match.group(0):
            return match.group(0)
        return f'src="{path}?v={sha}"'

    html = re.sub(r'href="([^"?]+\.css)"', css_repl, html)
    html = re.sub(r'src="([^"?]+\.(?:png|svg|js|pdf))"', src_repl, html)
    html = re.sub(r'href="([^"?]+\.pdf)"', css_repl, html)
    return html


def main() -> None:
    sha = git_short_sha()
    for template in sorted(SITE.glob("*.template.html")):
        dst = SITE / template.name.replace(".template.html", ".html")
        text = template.read_text(encoding="utf-8")
        dst.write_text(inject(text, sha), encoding="utf-8")
        print(f"Wrote {dst.name} (v={sha})")


if __name__ == "__main__":
    main()
