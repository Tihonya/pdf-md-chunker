from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple


from unstructured.partition.pdf import partition_pdf
# type: ignore

try:
    import pdfplumber  # type: ignore
except ImportError:  # pragma: no cover
    pdfplumber = None  # type: ignore

logger = logging.getLogger(__name__)


def extract_blocks(pdf_path: Path) -> List[Tuple[str, int]]:
    """Return list of (text, page_no) blocks (one per paragraph)."""
    if partition_pdf is not None:
        try:
            elements = partition_pdf(filename=str(pdf_path))
            blocks: List[Tuple[str, int]] = []
            for el in elements:
                if hasattr(el, "text") and (txt := el.text.strip()):
                    blocks.append((txt, el.metadata.page_number or 0))
            return blocks
        except Exception as e:  # fallback
            logger.warning("unstructured failed, fallback to pdfplumber: %s", e)
    # fallback
    if pdfplumber is None:
        raise RuntimeError(
            "Немає доступного парсера PDF: ні 'unstructured', ні 'pdfplumber'."
        )
    blocks_fallback: List[Tuple[str, int]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    blocks_fallback.append((para, i))
    return blocks_fallback


def extract_content(
    pdf_path: Path,
) -> Tuple[List[Tuple[str, int]], List[Tuple[bytes, int]]]:
    """Return (blocks, images) where images is list of (bytes, page_no)."""
    blocks = extract_blocks(pdf_path)
    images: List[Tuple[bytes, int]] = []

    if partition_pdf is not None:
        try:
            elements = partition_pdf(filename=str(pdf_path))
            for el in elements:
                if el.category == "Image" and hasattr(el, "raw_bytes") and el.raw_bytes:  # type: ignore[attr-defined]
                    images.append((bytes(el.raw_bytes), el.metadata.page_number or 0))  # type: ignore[arg-type]
        except Exception:  # pragma: no cover
            pass

    if not images and pdfplumber is not None:
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    for img in page.images:
                        extracted = page.extract_image(img["xref"])  # type: ignore[attr-defined]
                        if extracted and "image" in extracted:
                            images.append((extracted["image"], i))
        except Exception:  # pragma: no cover
            pass

    return blocks, images 