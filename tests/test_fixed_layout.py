import fitz
import pytest
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

from fixed_layout import write_fixed_layout
from pdf_fixtures import (
    FORM_FILLED_LINES,
    make_form_filled_pdf,
    make_multi_page_text_pdf,
    make_scanned_pdf,
)


def convert(tmp_path, pdf_path):
    output_path = tmp_path / "out.docx"
    write_fixed_layout(str(pdf_path), str(output_path))
    return Document(str(output_path))


def text_paragraphs(document):
    return [p for p in document.paragraphs if p.text.strip()]


def visible_lines(document):
    return [p.text.replace("\t", "") for p in text_paragraphs(document)]


def floating_images(document):
    return document.element.body.findall(".//" + qn("wp:anchor"))


def build_pdf(tmp_path, draw, width=595, height=842, rotation=0):
    path = tmp_path / "in.pdf"
    pdf = fitz.open()
    page = pdf.new_page(width=width, height=height)
    draw(page)
    page.set_rotation(rotation)
    pdf.save(str(path))
    pdf.close()
    return path


def test_form_reads_in_visual_order_with_fields_inside_sentences(tmp_path):
    pdf_path = tmp_path / "form.pdf"
    make_form_filled_pdf(pdf_path)

    document = convert(tmp_path, pdf_path)

    assert visible_lines(document) == FORM_FILLED_LINES


def test_form_is_not_turned_into_tables_or_columns(tmp_path):
    pdf_path = tmp_path / "form.pdf"
    make_form_filled_pdf(pdf_path)

    document = convert(tmp_path, pdf_path)

    assert document.tables == []
    assert len(document.sections) == 1
    assert document.sections[0]._sectPr.xpath("./w:cols/@w:num") in ([], ["1"])


def test_lines_are_placed_at_their_pdf_coordinates(tmp_path):
    def draw(page):
        page.insert_text((100, 100), "左", fontname="china-s", fontsize=12)
        page.insert_text((300, 100), "右", fontname="china-s", fontsize=12)
        page.insert_text((150, 200), "下", fontname="china-s", fontsize=12)

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    first, second = text_paragraphs(document)
    assert first.paragraph_format.left_indent == pytest.approx(Pt(100), abs=Pt(2))
    assert [stop.position for stop in first.paragraph_format.tab_stops] == [
        pytest.approx(Pt(300), abs=Pt(2))
    ]
    assert second.paragraph_format.left_indent == pytest.approx(Pt(150), abs=Pt(2))
    assert second.paragraph_format.space_before == pytest.approx(Pt(88), abs=Pt(4))


def test_text_keeps_size_bold_and_color(tmp_path):
    def draw(page):
        page.insert_text(
            (100, 100), "Title", fontname="hebo", fontsize=20, color=(1, 0, 0)
        )

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    run = text_paragraphs(document)[0].runs[-1]
    assert run.font.size == Pt(20)
    assert run.font.bold is True
    assert str(run.font.color.rgb) == "FF0000"


def test_spaces_between_words_are_kept(tmp_path):
    def draw(page):
        page.insert_text((72, 100), "Hello big world", fontname="helv", fontsize=12)

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    assert visible_lines(document) == ["Hello big world"]


def test_body_spaces_under_a_field_do_not_split_its_text(tmp_path):
    def draw(page):
        page.insert_text((72, 100), "ID:" + " " * 40 + "end", fontname="helv", fontsize=12)
        page.insert_text((100, 100), "1234567890", fontname="helv", fontsize=12)

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    assert "1234567890" in visible_lines(document)[0]


def test_lines_overflow_rather_than_wrap_and_push_later_lines_down(tmp_path):
    def draw(page):
        page.insert_text((72, 100), "line", fontname="helv", fontsize=12)

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    assert text_paragraphs(document)[0].paragraph_format.right_indent < 0


def test_invisible_ocr_layer_is_dropped(tmp_path):
    def draw(page):
        page.insert_text((72, 100), "shown", fontname="helv", fontsize=12)
        page.insert_text((72, 200), "ocr", fontname="helv", fontsize=12, render_mode=3)

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    assert visible_lines(document) == ["shown"]


def test_white_text_on_dark_background_is_kept(tmp_path):
    def draw(page):
        page.draw_rect(fitz.Rect(60, 80, 300, 120), fill=(0, 0, 0), color=(0, 0, 0))
        page.insert_text((72, 105), "header", fontname="helv", fontsize=12, color=(1, 1, 1))
        page.insert_text((72, 300), "hidden", fontname="helv", fontsize=12, color=(1, 1, 1))

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    assert visible_lines(document) == ["header"]


def test_graphics_become_one_page_sized_image_behind_the_text(tmp_path):
    pdf_path = tmp_path / "form.pdf"
    make_form_filled_pdf(pdf_path)

    document = convert(tmp_path, pdf_path)

    anchors = floating_images(document)
    assert len(anchors) == 1
    assert anchors[0].get("behindDoc") == "1"
    extent = anchors[0].find(qn("wp:extent"))
    assert int(extent.get("cx")) == pytest.approx(Pt(595), abs=Pt(1))
    assert int(extent.get("cy")) == pytest.approx(Pt(842), abs=Pt(1))


def test_text_only_page_has_no_background_image(tmp_path):
    def draw(page):
        page.insert_text((72, 100), "plain", fontname="helv", fontsize=12)

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    assert floating_images(document) == []


def test_background_does_not_contain_the_text(tmp_path):
    def draw(page):
        page.draw_line((72, 110), (300, 110), color=(0, 0, 0), width=1)
        page.insert_text((72, 100), "MMMMMMMM", fontname="helv", fontsize=40)

    document = convert(tmp_path, build_pdf(tmp_path, draw))

    blip = floating_images(document)[0].find(".//" + qn("a:blip"))
    image = document.part.related_parts[blip.get(qn("r:embed"))].blob
    pixmap = fitz.Pixmap(image)
    scale = pixmap.width / 595
    # Inside the glyphs' band, above the rule: nothing may have been painted.
    alphas = {
        pixmap.pixel(int(x * scale), int(85 * scale))[-1] for x in range(75, 280, 3)
    }
    assert alphas == {0}


def test_each_page_gets_its_own_section_and_size(tmp_path):
    path = tmp_path / "in.pdf"
    pdf = fitz.open()
    for width, height, value in ((595, 842, "first"), (842, 595, "second")):
        pdf.new_page(width=width, height=height).insert_text(
            (72, 100), value, fontname="helv", fontsize=12
        )
    pdf.save(str(path))
    pdf.close()

    document = convert(tmp_path, path)

    sizes = [(s.page_width, s.page_height) for s in document.sections]
    assert sizes == [
        (pytest.approx(Pt(595), abs=Pt(1)), pytest.approx(Pt(842), abs=Pt(1))),
        (pytest.approx(Pt(842), abs=Pt(1)), pytest.approx(Pt(595), abs=Pt(1))),
    ]
    assert visible_lines(document) == ["first", "second"]


def test_multi_page_text_stays_in_page_order(tmp_path):
    pdf_path = tmp_path / "pages.pdf"
    make_multi_page_text_pdf(pdf_path, 3)

    document = convert(tmp_path, pdf_path)

    assert visible_lines(document) == ["第1页内容", "第2页内容", "第3页内容"]
    assert len(document.sections) == 3


def test_scanned_page_is_kept_as_background(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    make_scanned_pdf(pdf_path)

    document = convert(tmp_path, pdf_path)

    assert visible_lines(document) == []
    assert len(floating_images(document)) == 1


def test_rotated_page_uses_rotated_geometry(tmp_path):
    def draw(page):
        page.insert_text((72, 100), "rotated", fontname="helv", fontsize=12)
        page.draw_line((72, 110), (300, 110), color=(0, 0, 0), width=1)

    document = convert(tmp_path, build_pdf(tmp_path, draw, rotation=90))

    section = document.sections[0]
    assert section.page_width == pytest.approx(Pt(842), abs=Pt(1))
    assert section.page_height == pytest.approx(Pt(595), abs=Pt(1))
    assert len(floating_images(document)) == 1

    # Rendering shows where a viewer actually sees the ink, at 1 pixel per point.
    pdf = fitz.open(str(tmp_path / "in.pdf"))
    pixmap = pdf[0].get_pixmap(dpi=72, colorspace=fitz.csGRAY)
    pdf.close()
    ink = [
        (x, y)
        for x in range(pixmap.width)
        for y in range(pixmap.height)
        if pixmap.pixel(x, y)[0] < 128
    ]
    ink_left = min(x for x, _ in ink)
    ink_right = max(x for x, _ in ink)
    ink_top = min(y for _, y in ink)

    paragraphs = text_paragraphs(document)
    assert "".join(p.text.replace("\t", "") for p in paragraphs) == "rotated"
    fmt = paragraphs[0].paragraph_format
    assert Pt(ink_left - 3) <= fmt.left_indent <= Pt(ink_right + 3)
    assert fmt.space_before == pytest.approx(Pt(ink_top), abs=Pt(3))
