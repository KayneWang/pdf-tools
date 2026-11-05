import os
import subprocess
import sys

from docx import Document

from pdf_fixtures import (
    FORM_FILLED_LINES,
    make_document_pdf,
    make_empty_pdf,
    make_encrypted_pdf,
    make_form_filled_pdf,
    make_pdf,
    make_scanned_pdf,
)

CLI_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdf"
)
SCANNED_WARNING = "警告：未检测到可编辑文字，可能是扫描件，内容将以图片形式保留"


def run_cli(args, cwd, input_text=None):
    return subprocess.run(
        [sys.executable, CLI_PATH] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        input=input_text,
    )


def test_cli_extracts_images_to_default_output_dir(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[2])

    result = run_cli(["extract-images", "sample.pdf"], cwd=tmp_path)

    assert result.returncode == 0
    assert "提取到 2 张图片" in result.stdout
    output_dir = tmp_path / "sample_images"
    assert output_dir.is_dir()
    assert len(list(output_dir.iterdir())) == 2


def test_cli_extracts_images_to_custom_output_dir(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[1])

    result = run_cli(["extract-images", "sample.pdf", "-o", "myout"], cwd=tmp_path)

    assert result.returncode == 0
    output_dir = tmp_path / "myout"
    assert output_dir.is_dir()
    assert len(list(output_dir.iterdir())) == 1


def test_cli_reports_no_images_found(tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    make_empty_pdf(pdf_path)

    result = run_cli(["extract-images", "empty.pdf"], cwd=tmp_path)

    assert result.returncode == 0
    assert "未找到图片" in result.stdout


def test_cli_fails_on_missing_input_file(tmp_path):
    result = run_cli(["extract-images", "does_not_exist.pdf"], cwd=tmp_path)

    assert result.returncode != 0
    assert "does_not_exist.pdf" in result.stderr


def test_cli_fails_on_invalid_pdf(tmp_path):
    bad_path = tmp_path / "broken.pdf"
    bad_path.write_bytes(b"not a real pdf")

    result = run_cli(["extract-images", "broken.pdf"], cwd=tmp_path)

    assert result.returncode != 0
    assert "错误" in result.stderr


def test_cli_rejects_old_form_without_subcommand(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[1])

    result = run_cli(["sample.pdf"], cwd=tmp_path)

    assert result.returncode != 0
    assert "错误：未知的子命令: sample.pdf" in result.stderr
    assert "extract-images" in result.stderr
    assert "to-word" in result.stderr
    assert not (tmp_path / "sample_images").exists()


def test_to_word_writes_default_output_silently(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")

    result = run_cli(["to-word", "doc.pdf"], cwd=tmp_path)

    assert result.returncode == 0
    assert result.stderr == ""
    assert "正在转换…" in result.stdout
    assert "已转换为 Word，已保存到: doc.docx" in result.stdout
    document = Document(str(tmp_path / "doc.docx"))
    assert "第一章 概述" in "\n".join(p.text for p in document.paragraphs)


def test_to_word_writes_custom_output_and_creates_parents(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")

    result = run_cli(["to-word", "doc.pdf", "-o", "a/b/out.docx"], cwd=tmp_path)

    assert result.returncode == 0
    assert (tmp_path / "a" / "b" / "out.docx").is_file()


def test_to_word_refuses_to_overwrite_existing_output(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")
    output_path = tmp_path / "doc.docx"
    output_path.write_bytes(b"edited by hand")

    result = run_cli(["to-word", "doc.pdf"], cwd=tmp_path)

    assert result.returncode != 0
    assert "错误：输出文件已存在: doc.docx" in result.stderr
    assert output_path.read_bytes() == b"edited by hand"


def test_to_word_force_overwrites_existing_output(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")
    output_path = tmp_path / "doc.docx"
    output_path.write_bytes(b"edited by hand")

    result = run_cli(["to-word", "doc.pdf", "--force"], cwd=tmp_path)

    assert result.returncode == 0
    assert len(Document(str(output_path)).tables) == 1


def test_to_word_requires_docx_suffix(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")

    result = run_cli(["to-word", "doc.pdf", "-o", "out.doc"], cwd=tmp_path)

    assert result.returncode != 0
    assert "错误：输出文件必须以 .docx 结尾: out.doc" in result.stderr
    assert not (tmp_path / "out.doc").exists()


def test_to_word_fails_on_missing_input_file(tmp_path):
    result = run_cli(["to-word", "does_not_exist.pdf"], cwd=tmp_path)

    assert result.returncode != 0
    assert "错误：输入文件不存在: does_not_exist.pdf" in result.stderr


def test_to_word_fails_on_invalid_pdf_without_leaving_output(tmp_path):
    (tmp_path / "broken.pdf").write_bytes(b"not a real pdf")

    result = run_cli(["to-word", "broken.pdf"], cwd=tmp_path)

    assert result.returncode == 1
    assert "错误：无法处理PDF文件:" in result.stderr
    assert [p.name for p in tmp_path.iterdir()] == ["broken.pdf"]


def test_to_word_reports_password_protected_pdf(tmp_path):
    make_encrypted_pdf(tmp_path / "secret.pdf")

    result = run_cli(["to-word", "secret.pdf"], cwd=tmp_path)

    assert result.returncode == 1
    assert "错误：PDF 已加密，需要密码: secret.pdf" in result.stderr
    assert not (tmp_path / "secret.docx").exists()


def test_to_word_warns_about_scanned_pdf_but_succeeds(tmp_path):
    make_scanned_pdf(tmp_path / "scan.pdf")

    result = run_cli(["to-word", "scan.pdf"], cwd=tmp_path)

    assert result.returncode == 0
    assert SCANNED_WARNING in result.stderr
    assert (tmp_path / "scan.docx").is_file()


def form_lines(path):
    document = Document(str(path))
    return [p.text.replace("\t", "") for p in document.paragraphs if p.text.strip()]


def test_to_word_fixed_layout_keeps_form_order(tmp_path):
    make_form_filled_pdf(tmp_path / "form.pdf")

    result = run_cli(["to-word", "form.pdf", "--layout", "fixed"], cwd=tmp_path)

    assert result.returncode == 0
    assert result.stderr == ""
    assert "已转换为 Word，已保存到: form.docx" in result.stdout
    assert form_lines(tmp_path / "form.docx") == FORM_FILLED_LINES


def test_to_word_flow_layout_is_the_default(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")

    result = run_cli(["to-word", "doc.pdf"], cwd=tmp_path)
    explicit = run_cli(
        ["to-word", "doc.pdf", "-o", "explicit.docx", "--layout", "flow"], cwd=tmp_path
    )

    assert result.returncode == 0
    assert explicit.returncode == 0
    # The sample's table survives only through flow layout's structure detection.
    assert len(Document(str(tmp_path / "doc.docx")).tables) == 1
    assert len(Document(str(tmp_path / "explicit.docx")).tables) == 1


def test_to_word_fixed_layout_warns_about_scanned_pdf(tmp_path):
    make_scanned_pdf(tmp_path / "scan.pdf")

    result = run_cli(["to-word", "scan.pdf", "--layout", "fixed"], cwd=tmp_path)

    assert result.returncode == 0
    assert SCANNED_WARNING in result.stderr


def test_to_word_fixed_layout_reports_password_protected_pdf(tmp_path):
    make_encrypted_pdf(tmp_path / "secret.pdf")

    result = run_cli(["to-word", "secret.pdf", "--layout", "fixed"], cwd=tmp_path)

    assert result.returncode == 1
    assert "错误：PDF 已加密，需要密码: secret.pdf" in result.stderr


def test_menu_converts_to_word_with_fixed_layout(tmp_path):
    make_form_filled_pdf(tmp_path / "form.pdf")

    result = run_cli([], cwd=tmp_path, input_text="2\nform.pdf\n\n2\n")

    assert result.returncode == 0
    assert "版式（1. 流式，适合长文档；2. 固定，适合证明和表单）[1]: " in result.stdout
    assert form_lines(tmp_path / "form.docx") == FORM_FILLED_LINES


def test_menu_rejects_invalid_layout_number(tmp_path):
    make_form_filled_pdf(tmp_path / "form.pdf")

    result = run_cli([], cwd=tmp_path, input_text="2\nform.pdf\n\n9\n")

    assert result.returncode != 0
    assert "错误：无效的版式编号: 9" in result.stderr
    assert not (tmp_path / "form.docx").exists()


def test_menu_extracts_images_with_defaults(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[2])

    result = run_cli([], cwd=tmp_path, input_text="1\nsample.pdf\n\n")

    assert result.returncode == 0
    assert "支持的功能" in result.stdout
    assert "提取到 2 张图片" in result.stdout
    output_dir = tmp_path / "sample_images"
    assert output_dir.is_dir()
    assert len(list(output_dir.iterdir())) == 2


def test_menu_empty_choice_defaults_to_first_feature(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    make_pdf(pdf_path, images_per_page=[1])

    result = run_cli([], cwd=tmp_path, input_text="\nsample.pdf\nmyout\n")

    assert result.returncode == 0
    output_dir = tmp_path / "myout"
    assert output_dir.is_dir()
    assert len(list(output_dir.iterdir())) == 1


def test_menu_converts_to_word_with_defaults(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")

    result = run_cli([], cwd=tmp_path, input_text="2\ndoc.pdf\n\n\n")

    assert result.returncode == 0
    assert "2. 转 Word" in result.stdout
    assert "输出文件（回车使用默认 doc.docx）" in result.stdout
    assert "已转换为 Word，已保存到: doc.docx" in result.stdout
    assert (tmp_path / "doc.docx").is_file()


def test_menu_converts_to_word_with_custom_output(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")

    result = run_cli([], cwd=tmp_path, input_text="2\ndoc.pdf\nout.docx\n\n")

    assert result.returncode == 0
    assert (tmp_path / "out.docx").is_file()


def test_menu_to_word_refuses_to_overwrite_existing_output(tmp_path):
    make_document_pdf(tmp_path / "doc.pdf")
    output_path = tmp_path / "doc.docx"
    output_path.write_bytes(b"edited by hand")

    result = run_cli([], cwd=tmp_path, input_text="2\ndoc.pdf\n\n\n")

    assert result.returncode != 0
    assert "错误：输出文件已存在: doc.docx" in result.stderr
    assert output_path.read_bytes() == b"edited by hand"


def test_menu_rejects_invalid_feature_number(tmp_path):
    result = run_cli([], cwd=tmp_path, input_text="9\n")

    assert result.returncode != 0
    assert "无效的功能编号" in result.stderr


def test_menu_fails_on_missing_pdf_path(tmp_path):
    result = run_cli([], cwd=tmp_path, input_text="1\ndoes_not_exist.pdf\n")

    assert result.returncode != 0
    assert "输入文件不存在" in result.stderr


def test_menu_fails_on_empty_pdf_path(tmp_path):
    result = run_cli([], cwd=tmp_path, input_text="1\n\n")

    assert result.returncode != 0
    assert "未输入 PDF 路径" in result.stderr


def test_help_describes_all_modes_in_chinese(tmp_path):
    result = run_cli(["--help"], cwd=tmp_path)

    assert result.returncode == 0
    assert "提取内嵌图片" in result.stdout
    assert "转换为 Word" in result.stdout
    assert "extract-images" in result.stdout
    assert "to-word" in result.stdout
    assert "交互式菜单" in result.stdout


def test_extract_images_help_is_in_chinese(tmp_path):
    result = run_cli(["extract-images", "--help"], cwd=tmp_path)

    assert result.returncode == 0
    assert "待提取图片的 PDF 文件路径" in result.stdout
    assert "图片输出目录" in result.stdout


def test_to_word_help_is_in_chinese(tmp_path):
    result = run_cli(["to-word", "--help"], cwd=tmp_path)

    assert result.returncode == 0
    assert "待转换的 PDF 文件路径" in result.stdout
    assert "输出文件路径" in result.stdout
    assert "覆盖已存在的输出文件" in result.stdout
    assert "--layout" in result.stdout
    assert "证明和表单" in result.stdout
