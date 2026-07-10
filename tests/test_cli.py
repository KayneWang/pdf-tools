import os
import subprocess
import sys

import fitz

from pdf_fixtures import make_pdf

CLI_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extract_images.py"
)


def run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, CLI_PATH] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_cli_extracts_images_to_default_output_dir(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[2])

    result = run_cli(["sample.pdf"], cwd=tmp_path)

    assert result.returncode == 0
    assert "提取到 2 张图片" in result.stdout
    output_dir = tmp_path / "sample_images"
    assert output_dir.is_dir()
    assert len(list(output_dir.iterdir())) == 2


def test_cli_extracts_images_to_custom_output_dir(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[1])

    result = run_cli(["sample.pdf", "-o", "myout"], cwd=tmp_path)

    assert result.returncode == 0
    output_dir = tmp_path / "myout"
    assert output_dir.is_dir()
    assert len(list(output_dir.iterdir())) == 1


def test_cli_reports_no_images_found(tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    result = run_cli(["empty.pdf"], cwd=tmp_path)

    assert result.returncode == 0
    assert "未找到图片" in result.stdout


def test_cli_fails_on_missing_input_file(tmp_path):
    result = run_cli(["does_not_exist.pdf"], cwd=tmp_path)

    assert result.returncode != 0
    assert "does_not_exist.pdf" in result.stderr


def test_cli_fails_on_invalid_pdf(tmp_path):
    bad_path = tmp_path / "broken.pdf"
    bad_path.write_bytes(b"not a real pdf")

    result = run_cli(["broken.pdf"], cwd=tmp_path)

    assert result.returncode != 0
    assert "错误" in result.stderr
