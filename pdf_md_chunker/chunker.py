from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from rapidfuzz import fuzz

from .utils import token_count


@dataclass
class Chunk:
    text: str
    page_start: int
    page_end: int
    tokens: int = field(init=False)

    def __post_init__(self):
        self.tokens = token_count(self.text)


class Chunker:
    """Chunker implementing spec: break at headings else sliding window."""

    def __init__(
        self,
        target_tokens: int = 1500,
        max_tokens: int = 3200,
        quality_threshold: float = 0.9,
        outline_pages: set[int] | None = None,
    ) -> None:
        self.target = target_tokens
        self.max = max_tokens
        self.quality = quality_threshold * 100  # rapidfuzz ratio 0-100
        self.outline_pages = outline_pages or set()

    def deduplicate(self, chunks: List[Chunk]) -> List[Chunk]:
        unique: List[Chunk] = []
        for chunk in chunks:
            if not any(
                fuzz.token_set_ratio(chunk.text, c.text) >= self.quality for c in unique
            ):
                unique.append(chunk)
        return unique

    def split_blocks(self, blocks: Sequence[tuple[str, int]]) -> List[Chunk]:
        """blocks: list of (text,page_no) already cleaned & merged heading lines."""
        chunks: List[Chunk] = []
        buf: List[str] = []
        pages: List[int] = []
        tok = 0
        for text, page in blocks:
            t = token_count(text)
            # if adding exceeds hard max → flush current buffer
            if buf and tok + t > self.max:
                chunks.append(
                    Chunk(text="\n\n".join(buf), page_start=pages[0], page_end=pages[-1])
                )
                buf, pages, tok = [], [], 0
            buf.append(text)
            pages.append(page)
            tok += t
            # if passed target and (outline break or heading marker) → flush
            if tok >= self.target and (
                page in self.outline_pages or text.strip().endswith("\n#") or len(buf) > 1
            ):
                chunks.append(
                    Chunk(text="\n\n".join(buf), page_start=pages[0], page_end=pages[-1])
                )
                buf, pages, tok = [], [], 0
        if buf:
            chunks.append(Chunk(text="\n\n".join(buf), page_start=pages[0], page_end=pages[-1]))
        return self.deduplicate(chunks) 