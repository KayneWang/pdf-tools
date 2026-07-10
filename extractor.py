"""Core logic for extracting embedded images from a PDF file."""
import os

import fitz


def extract_images(pdf_path, output_dir):
    """Extract every embedded image from `pdf_path` into `output_dir`.

    Files are named `page{N}_img{M}.{ext}` (1-based page number N, 1-based
    per-page image index M, ext from PyMuPDF's detected image format).
    Creates `output_dir` (including parent dirs) if it doesn't exist.
    Returns the list of file paths written, in extraction order.
    """
    os.makedirs(output_dir, exist_ok=True)
    saved_paths = []

    doc = fitz.open(pdf_path)
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            for img_index, img in enumerate(page.get_images(full=True), start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                filename = f"page{page_index + 1}_img{img_index}.{base_image['ext']}"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(base_image["image"])
                saved_paths.append(filepath)
    finally:
        doc.close()

    return saved_paths
