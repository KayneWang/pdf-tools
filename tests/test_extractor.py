import os
import re

from extractor import extract_images
from pdf_fixtures import make_empty_pdf, make_pdf


def test_extract_images_from_multi_page_pdf(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[1, 2])  # page1: 1 image, page2: 2 images
    output_dir = tmp_path / "out"

    saved = extract_images(str(pdf_path), str(output_dir))

    assert len(saved) == 3
    pattern = re.compile(r"^page(1_img1|2_img1|2_img2)\.\w+$")
    for filepath in saved:
        assert os.path.isfile(filepath)
        assert os.path.getsize(filepath) > 0
        assert pattern.match(os.path.basename(filepath)), filepath


def test_extract_images_from_pdf_without_images(tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    make_empty_pdf(pdf_path)
    output_dir = tmp_path / "out"

    saved = extract_images(str(pdf_path), str(output_dir))

    assert saved == []
    assert os.path.isdir(output_dir)


def test_creates_output_directory_if_missing(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[1])
    output_dir = tmp_path / "nested" / "out"

    saved = extract_images(str(pdf_path), str(output_dir))

    assert os.path.isdir(output_dir)
    assert len(saved) == 1


def test_overwrites_existing_files_in_output_dir(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[1])
    output_dir = tmp_path / "out"

    first = extract_images(str(pdf_path), str(output_dir))
    second = extract_images(str(pdf_path), str(output_dir))

    assert first == second
    assert len(second) == 1
