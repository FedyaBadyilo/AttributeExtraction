"""PDF page rendering for the lab VLM bench."""

from __future__ import annotations

import base64
from pathlib import Path

import fitz


def count_pdf_pages(pdf_path: Path) -> int:
    document = fitz.open(pdf_path)
    try:
        return document.page_count
    finally:
        document.close()


def render_pdf_pages_png(*, pdf_path: Path, dpi: int) -> list[bytes]:
    """Render each PDF page to PNG bytes at the given DPI."""
    if dpi <= 0:
        raise ValueError(f"dpi must be positive, got {dpi}")

    document = fitz.open(pdf_path)
    try:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pages: list[bytes] = []
        for page in document:
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            pages.append(pixmap.tobytes("png"))
        return pages
    finally:
        document.close()


def png_to_data_url(png_bytes: bytes) -> str:
    encoded = base64.standard_b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


__all__ = ["count_pdf_pages", "png_to_data_url", "render_pdf_pages_png"]
