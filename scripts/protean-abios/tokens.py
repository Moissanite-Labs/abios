"""Multi-tokenizer counting utilities for ABIOS/3 bench and lexicon generation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

LEXICON_PATH = Path(__file__).resolve().parent / "lexicon.json"


@dataclass(frozen=True)
class TokenizerSpec:
    name: str
    encode: Callable[[str], list[int]]


def required_tokenizer_names() -> list[str]:
    data = json.loads(LEXICON_PATH.read_text(encoding="utf-8"))
    names = data.get("tokenizers")
    if not isinstance(names, list) or not names:
        raise RuntimeError("lexicon.json missing tokenizers list")
    return [str(n) for n in names]


def load_tokenizers(*, strict: bool = True) -> list[TokenizerSpec]:
    """Load exactly the tokenizers listed in lexicon.json (fail closed by default)."""
    required = required_tokenizer_names()
    specs: list[TokenizerSpec] = []
    errors: list[str] = []

    try:
        import tiktoken
    except ImportError as exc:
        if strict:
            raise RuntimeError("tiktoken is required for ABIOS bench and lexicon generation") from exc
        return []

    for name in required:
        try:
            enc = tiktoken.get_encoding(name)
            specs.append(TokenizerSpec(name, enc.encode))
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if strict and (errors or len(specs) != len(required)):
        detail = "; ".join(errors) if errors else f"got {len(specs)} of {len(required)}"
        raise RuntimeError(f"failed to load lexicon tokenizers ({detail})")

    return specs


def token_count(text: str, spec: TokenizerSpec) -> int:
    return len(spec.encode(text))


def max_token_count(text: str, specs: list[TokenizerSpec]) -> int:
    if not specs:
        raise RuntimeError("no tokenizers loaded")
    return max(token_count(text, s) for s in specs)


def is_single_token(text: str, specs: list[TokenizerSpec]) -> bool:
    return all(token_count(text, s) == 1 for s in specs)


def pick_cheapest(candidates: list[str], specs: list[TokenizerSpec]) -> tuple[str, int]:
    """Return candidate with lowest max tokenizer count; tie-break shorter string."""
    best = candidates[0]
    best_score = max_token_count(best, specs)
    for c in candidates[1:]:
        score = max_token_count(c, specs)
        if score < best_score or (score == best_score and len(c) < len(best)):
            best, best_score = c, score
    return best, best_score
