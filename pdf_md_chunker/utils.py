from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, List

import tiktoken  # type: ignore

__all__ = [
    "slugify",
    "token_count",
    "sha256sum",
]


_slug_re = re.compile(r"[^a-z0-9]+")

token_encoder = (
    tiktoken.get_encoding("cl100k_base") if tiktoken is not None else None
)


def slugify(text: str) -> str:
    """Return ASCII-lowercase slug (spaces→-, keep alnum)."""
    text_ascii = (
        text.encode("ascii", "ignore").decode().lower().strip()  # remove non-ascii
    )
    slug = _slug_re.sub("-", text_ascii).strip("-")
    return slug


def token_count(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoder."""
    if token_encoder is None:
        raise RuntimeError(
            "Пакет 'tiktoken' не встановлено. Встановіть його або не викликайте token_count без нього."
        )
    return len(token_encoder.encode(text))


def sha256sum(path: Path | str) -> str:
    """Return sha256 checksum of a file as hex string."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest() 