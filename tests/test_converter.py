import logging
import os
import subprocess
import sys

import pytest
from docx import Document

from converter import PdfEncryptedError, convert_to_word, has_editable_text
from pdf_fixtures import (
    FORM_FILLED_LINES,
    make_document_pdf,
    make_encrypted_pdf,
    make_form_filled_pdf,
    make_multi_page_text_pdf,
    make_scanned_pdf,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fail_on_first_page(monkeypatch, error):
    from pdf2docx.page.Page import Page

    original_parse = Page.parse
    calls = []

    def parse(self, *args, **kwargs):
        calls.append(self)
        if len(calls) == 1:
            raise error
        return original_parse(self, *args, **kwargs)

    monkeypatch.setattr(Page, "parse", parse)


def test_convert_keeps_text_table_and_image(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    make_document_pdf(pdf_path)
    output_path = tmp_path / "doc.docx"

    convert_to_word(str(pdf_path), str(output_path))

    document = Document(str(output_path))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "第一章 概述" in text
    assert "这是一段中文正文。" in text
    assert len(document.tables) == 1
    cells = [
        [cell.text.strip() for cell in row.cells] for row in document.tables[0].rows
    ]
    assert cells == [["姓名", "年龄"], ["张三", "30"]]
    assert len(document.inline_shapes) == 1


def test_convert_creates_missing_parent_directories(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    make_document_pdf(pdf_path)
    output_path = tmp_path / "nested" / "dir" / "doc.docx"

    convert_to_word(str(pdf_path), str(output_path))

    assert output_path.is_file()


def test_convert_leaves_nothing_behind_when_pdf_is_invalid(tmp_path):
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_bytes(b"not a real pdf")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    with pytest.raises(Exception):
        convert_to_word(str(pdf_path), str(output_dir / "broken.docx"))

    assert list(output_dir.iterdir()) == []


def test_convert_fails_entirely_when_one_page_fails(tmp_path, monkeypatch):
    pdf_path = tmp_path / "two.pdf"
    make_multi_page_text_pdf(pdf_path, 2)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    _fail_on_first_page(monkeypatch, RuntimeError("boom"))

    with pytest.raises(Exception, match="boom"):
        convert_to_word(str(pdf_path), str(output_dir / "two.docx"))

    assert list(output_dir.iterdir()) == []


def test_failed_conversion_keeps_existing_output(tmp_path, monkeypatch):
    pdf_path = tmp_path / "two.pdf"
    make_multi_page_text_pdf(pdf_path, 2)
    output_path = tmp_path / "two.docx"
    output_path.write_bytes(b"edited by hand")
    _fail_on_first_page(monkeypatch, RuntimeError("boom"))

    with pytest.raises(Exception, match="boom"):
        convert_to_word(str(pdf_path), str(output_path))

    assert output_path.read_bytes() == b"edited by hand"


def test_interrupted_conversion_leaves_nothing_behind(tmp_path, monkeypatch):
    pdf_path = tmp_path / "two.pdf"
    make_multi_page_text_pdf(pdf_path, 2)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    _fail_on_first_page(monkeypatch, KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        convert_to_word(str(pdf_path), str(output_dir / "two.docx"))

    assert list(output_dir.iterdir()) == []


def test_convert_rejects_password_protected_pdf(tmp_path):
    pdf_path = tmp_path / "secret.pdf"
    make_encrypted_pdf(pdf_path)
    output_path = tmp_path / "secret.docx"

    with pytest.raises(PdfEncryptedError):
        convert_to_word(str(pdf_path), str(output_path))

    assert not output_path.exists()


def test_convert_restores_logging_afterwards(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    make_document_pdf(pdf_path)
    previous = logging.root.manager.disable

    convert_to_word(str(pdf_path), str(tmp_path / "doc.docx"))

    assert logging.root.manager.disable == previous


def test_has_editable_text_is_true_for_text_pdf(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    make_document_pdf(pdf_path)

    assert has_editable_text(str(pdf_path)) is True


def test_has_editable_text_is_false_for_scanned_pdf(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    make_scanned_pdf(pdf_path)

    assert has_editable_text(str(pdf_path)) is False


def test_fixed_layout_keeps_form_fields_inside_sentences(tmp_path):
    pdf_path = tmp_path / "form.pdf"
    make_form_filled_pdf(pdf_path)
    output_path = tmp_path / "form.docx"

    convert_to_word(str(pdf_path), str(output_path), layout="fixed")

    document = Document(str(output_path))
    lines = [p.text.replace("\t", "") for p in document.paragraphs if p.text.strip()]
    assert lines == FORM_FILLED_LINES


def test_fixed_layout_failure_keeps_existing_output(tmp_path, monkeypatch):
    import fixed_layout

    pdf_path = tmp_path / "form.pdf"
    make_form_filled_pdf(pdf_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    output_path = output_dir / "form.docx"
    output_path.write_bytes(b"edited by hand")

    def boom(*args):
        raise RuntimeError("boom")

    monkeypatch.setattr(fixed_layout, "_write_page", boom)

    with pytest.raises(RuntimeError, match="boom"):
        convert_to_word(str(pdf_path), str(output_path), layout="fixed")

    assert output_path.read_bytes() == b"edited by hand"
    assert [p.name for p in output_dir.iterdir()] == ["form.docx"]


def test_fixed_layout_rejects_password_protected_pdf(tmp_path):
    pdf_path = tmp_path / "secret.pdf"
    make_encrypted_pdf(pdf_path)

    with pytest.raises(PdfEncryptedError):
        convert_to_word(str(pdf_path), str(tmp_path / "secret.docx"), layout="fixed")


def test_unknown_layout_is_rejected(tmp_path):
    pdf_path = tmp_path / "form.pdf"
    make_form_filled_pdf(pdf_path)

    with pytest.raises(ValueError):
        convert_to_word(str(pdf_path), str(tmp_path / "x.docx"), layout="nope")


def test_importing_converter_does_not_load_pdf2docx():
    code = "import sys, converter; sys.exit('pdf2docx' in sys.modules)"

    result = subprocess.run([sys.executable, "-c", code], cwd=PROJECT_ROOT)

    assert result.returncode == 0
