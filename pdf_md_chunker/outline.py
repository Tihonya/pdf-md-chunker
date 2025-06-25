from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pikepdf

__all__ = ["parse_outline"]


def _walk(items, pdf: pikepdf.Pdf, max_depth: int, depth: int, acc: List[Tuple[str, int]]):
    for it in items:
        if it.destination is not None and depth <= max_depth:
            try:
                page_no = pdf.pages.index(it.destination.page) + 1  # 1-based
            except Exception:
                continue
            acc.append((str(it.title).strip(), page_no))
        if it.children:
            _walk(it.children, pdf, max_depth, depth + 1, acc)


def parse_outline(pdf_path: Path | str, max_depth: int = 2) -> List[Tuple[str, int]]:
    """Return list of (title, page_no) for outline entries up to ``max_depth``.

    Empty list if no outline or file lacks entries.
    """
    pdf_path = Path(pdf_path)
    result: List[Tuple[str, int]] = []
    try:
        with pikepdf.open(pdf_path) as pdf:
            outline_root = pdf.open_outline()
            if outline_root:
                _walk(list(outline_root), pdf, max_depth, 1, result)  # type: ignore[arg-type]
    except Exception:  # pragma: no cover
        return []
    return result 