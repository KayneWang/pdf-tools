"""Shared helpers for building test PDF fixtures with real embedded images."""
import base64

import fitz

# A minimal valid 1x1 pixel PNG (transparent), used to embed real,
# extractable images into test PDFs.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def make_pdf(path, images_per_page):
    """Create a PDF at `path` with one page per entry in `images_per_page`,
    embedding that many copies of PNG_BYTES as images on each page.

    Example: make_pdf(path, [1, 2]) creates a 2-page PDF where page 1 has
    1 embedded image and page 2 has 2 embedded images.
    """
    doc = fitz.open()
    for count in images_per_page:
        page = doc.new_page()
        for i in range(count):
            rect = fitz.Rect(10 + i * 20, 10, 20 + i * 20, 20)
            page.insert_image(rect, stream=PNG_BYTES)
    doc.save(str(path))
    doc.close()
