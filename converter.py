"""Core logic for converting a PDF file into a Word document."""
import logging
import os
import tempfile

import fitz

LAYOUT_FLOW = "flow"
LAYOUT_FIXED = "fixed"
LAYOUTS = (LAYOUT_FLOW, LAYOUT_FIXED)


class PdfEncryptedError(Exception):
    """The PDF needs a password to open."""


def convert_to_word(pdf_path, output_path, layout=LAYOUT_FLOW):
    """Convert `pdf_path` into the Word document `output_path`.

    `layout` is LAYOUT_FLOW, which infers paragraphs and tables so text can reflow,
    or LAYOUT_FIXED, which keeps every line where the PDF puts it.

    Creates missing parent directories and replaces an existing `output_path`.
    The conversion is all-or-nothing: if any page fails, or the run is
    interrupted, the exception propagates and `output_path` is left untouched.
    Raises PdfEncryptedError if the PDF needs a password.
    """
    if layout not in LAYOUTS:
        raise ValueError(f"unknown layout: {layout}")

    doc = fitz.open(pdf_path)
    try:
        if doc.needs_pass:
            raise PdfEncryptedError(pdf_path)
    finally:
        doc.close()

    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)

    # Build in a sibling temp dir so the final replace is atomic (same filesystem).
    with tempfile.TemporaryDirectory(dir=output_dir, prefix=".pdf-tools-") as temp_dir:
        temp_path = os.path.join(temp_dir, "output.docx")
        if layout == LAYOUT_FIXED:
            from fixed_layout import write_fixed_layout

            write_fixed_layout(pdf_path, temp_path)
        else:
            _run_pdf2docx(pdf_path, temp_path)
        os.replace(temp_path, output_path)


def has_editable_text(pdf_path):
    """Return whether any page of `pdf_path` contains extractable text."""
    doc = fitz.open(pdf_path)
    try:
        return any(page.get_text().strip() for page in doc)
    finally:
        doc.close()


def _run_pdf2docx(pdf_path, output_path):
    # Imported here because pdf2docx pulls in OpenCV, which would slow down
    # every other feature, and because it logs progress to stderr.
    from pdf2docx import Converter

    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        converter = Converter(pdf_path)
        try:
            # By default pdf2docx drops failed pages and still reports success.
            converter.convert(output_path, ignore_page_error=False)
        finally:
            converter.close()
    finally:
        logging.disable(previous_disable)
