"""Rebuild a PDF as a Word document from its coordinates, without inferring structure.

Each visual line becomes one paragraph, placed through its indent, exact line
height, space-before and tab stops. Everything that isn't text (underlines, table
borders, stamps, scans) is rendered into one transparent image behind the text.
"""
import copy
import io

import fitz
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Emu, Pt, RGBColor

BACKGROUND_DPI = 200
EMU_PER_POINT = 12700

# How far apart, as a fraction of font size, characters may be and still count as
# the same line (vertically) or the same run of text (horizontally).
SAME_LINE_TOLERANCE = 0.5
SAME_SEGMENT_GAP = 0.8
MIN_SPACE_GAP = 0.15

# Lets a line run off the page if a substituted font is wider than the original:
# wrapping would push every later line out of step with the background image.
NO_WRAP_RIGHT_INDENT = Pt(-400)

INVISIBLE_RENDER_MODE = 3
DARK_LUMINANCE = 128

# PDF font names that differ from what Word calls the same font.
WORD_FONT_NAMES = {"MicrosoftYaHei": "Microsoft YaHei", "STSong": "SimSun"}


def write_fixed_layout(pdf_path, output_path):
    """Write `pdf_path` to the Word document `output_path`, one section per page."""
    pdf = fitz.open(pdf_path)
    try:
        document = Document()
        document._body.clear_content()
        for index, page in enumerate(pdf):
            if index > 0:
                _shrink_to_nothing(_add_section_paragraph(document))
            _write_page(document, page, _render_background(pdf_path, index, page))
        document.save(output_path)
    finally:
        pdf.close()


def _add_section_paragraph(document):
    # python-docx closes the previous section with an empty paragraph of its own.
    document.add_section(WD_SECTION.NEW_PAGE)
    return document.paragraphs[-1]


def _shrink_to_nothing(paragraph):
    # So that the section's closing paragraph can't spill onto a page of its own.
    fmt = paragraph.paragraph_format
    fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    fmt.line_spacing = Pt(1)
    fmt.space_before = fmt.space_after = Pt(0)


def _write_page(document, page, background):
    section = document.sections[-1]
    section.page_width = Pt(page.rect.width)
    section.page_height = Pt(page.rect.height)
    section.left_margin = section.right_margin = Pt(0)
    section.top_margin = section.bottom_margin = Pt(0)
    section.header_distance = section.footer_distance = Pt(0)

    first_paragraph = None
    previous_bottom = 0.0
    for line in _visible_lines(page, background):
        paragraph = _write_line(document, line, previous_bottom)
        first_paragraph = first_paragraph or paragraph
        previous_bottom = line["bottom"]

    if background is not None:
        if first_paragraph is None:
            first_paragraph = document.add_paragraph()
            _shrink_to_nothing(first_paragraph)
        _add_background(first_paragraph, background, page.rect)


def _render_background(pdf_path, page_index, page):
    """Render everything but text transparently, or None if the page has only text."""
    if not page.get_drawings() and not page.get_images():
        return None

    pdf = fitz.open(pdf_path)
    try:
        clean_page = pdf[page_index]
        rotation = clean_page.rotation
        clean_page.set_rotation(0)
        clean_page.add_redact_annot(clean_page.rect)
        clean_page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE,
            graphics=fitz.PDF_REDACT_LINE_ART_NONE,
        )
        clean_page.set_rotation(rotation)
        return clean_page.get_pixmap(dpi=BACKGROUND_DPI, alpha=True)
    finally:
        pdf.close()


def _visible_lines(page, background):
    """Group what the eye can see into lines, top to bottom, each made of segments."""
    chars = _visible_chars(page, background)
    chars.sort(key=lambda char: char["middle"])

    lines = []
    for char in chars:
        if not char["text"].isspace():
            tolerance = char["size"] * SAME_LINE_TOLERANCE
            if lines and abs(lines[-1]["middle"] - char["middle"]) < tolerance:
                lines[-1]["chars"].append(char)
            else:
                lines.append({"middle": char["middle"], "chars": [char]})

    result = []
    for line in lines:
        result.append(
            {
                "top": min(char["top"] for char in line["chars"]),
                "bottom": max(char["bottom"] for char in line["chars"]),
                "segments": _segments(_with_spaces(line, chars)),
            }
        )
    return result


def _with_spaces(line, chars):
    """The line's characters left to right, plus the spaces lying within its height."""
    top = min(char["top"] for char in line["chars"])
    bottom = max(char["bottom"] for char in line["chars"])
    spaces = [
        char
        for char in chars
        if char["text"].isspace() and top <= char["middle"] <= bottom
    ]
    return sorted(line["chars"] + spaces, key=lambda char: char["x0"])


def _segments(chars):
    """Split left-to-right characters into same-style runs at each visible gap."""
    segments = []
    pending_space = False
    for char in chars:
        if char["text"].isspace():
            pending_space = bool(segments)
            continue
        last = segments[-1] if segments else None
        gap = char["x0"] - last["x1"] if last is not None else 0
        if (
            last is not None
            and last["style"] == char["style"]
            and gap < char["size"] * SAME_SEGMENT_GAP
        ):
            # A space only counts if it opens a gap: forms leave spaces in the body
            # text underneath the fields written over them.
            has_space = pending_space and gap >= char["size"] * MIN_SPACE_GAP
            last["text"] += (" " if has_space else "") + char["text"]
            last["x1"] = char["x1"]
        else:
            segments.append(
                {
                    "text": char["text"],
                    "x0": char["x0"],
                    "x1": char["x1"],
                    "style": char["style"],
                }
            )
        pending_space = False
    return segments


def _visible_chars(page, background):
    chars = []
    for span in page.get_texttrace():
        if span["type"] == INVISIBLE_RENDER_MODE or span["opacity"] == 0:
            continue
        visible_bbox = fitz.Rect(span["bbox"]) * page.rotation_matrix
        visible_bbox.normalize()
        if _is_white(span["color"]) and not _is_on_dark(background, visible_bbox):
            continue
        style = {
            "font": span["font"],
            "size": span["size"],
            "color": _rgb_hex(span["color"]),
            "bold": bool(span["flags"] & fitz.TEXT_FONT_BOLD) or "Bold" in span["font"],
            "italic": bool(span["flags"] & fitz.TEXT_FONT_ITALIC),
        }
        for unicode_value, _, _, bbox in span["chars"]:
            if unicode_value < 32 and unicode_value not in (9, 10, 13):
                continue
            x0, y0, x1, y1 = fitz.Rect(bbox) * page.rotation_matrix
            x0, x1 = min(x0, x1), max(x0, x1)
            y0, y1 = min(y0, y1), max(y0, y1)
            chars.append(
                {
                    "text": chr(unicode_value),
                    "x0": x0,
                    "x1": x1,
                    "top": y0,
                    "bottom": y1,
                    "middle": (y0 + y1) / 2,
                    "size": span["size"],
                    "style": style,
                }
            )
    return chars


def _is_white(color):
    return len(color) > 0 and all(value >= 0.99 for value in color)


def _is_on_dark(background, bbox):
    """Whether white text in `bbox` would be readable, judged across its whole width."""
    if background is None:
        return False
    x0, y0, x1, y1 = bbox
    scale = BACKGROUND_DPI / 72
    middle = int((y0 + y1) / 2 * scale)
    samples = [int((x0 + (x1 - x0) * step / 8) * scale) for step in range(9)]
    luminances = []
    for x in samples:
        if 0 <= x < background.width and 0 <= middle < background.height:
            r, g, b, alpha = background.pixel(x, middle)
            opacity = alpha / 255
            luminances.append(
                (0.299 * r + 0.587 * g + 0.114 * b) * opacity + 255 * (1 - opacity)
            )
    return bool(luminances) and sum(luminances) / len(luminances) < DARK_LUMINANCE


def _rgb_hex(color):
    if len(color) == 3:
        return "".join(f"{round(value * 255):02X}" for value in color)
    if len(color) == 1:
        return f"{round(color[0] * 255):02X}" * 3
    return "000000"


def _write_line(document, line, previous_bottom):
    paragraph = document.add_paragraph()
    fmt = paragraph.paragraph_format
    fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    fmt.line_spacing = Pt(max(line["bottom"] - line["top"], 1))
    fmt.space_before = Pt(max(line["top"] - previous_bottom, 0))
    fmt.space_after = Pt(0)

    cursor = line["segments"][0]["x0"]
    fmt.left_indent = Pt(cursor)
    fmt.right_indent = NO_WRAP_RIGHT_INDENT
    for segment in line["segments"]:
        if segment["x0"] > cursor + 0.5:
            fmt.tab_stops.add_tab_stop(Pt(segment["x0"]), WD_TAB_ALIGNMENT.LEFT)
            _add_run(paragraph, "\t", segment["style"])
        _add_run(paragraph, segment["text"], segment["style"])
        cursor = segment["x1"]
    return paragraph


def _add_run(paragraph, text, style):
    run = paragraph.add_run(text)
    run.font.size = Pt(round(style["size"] * 2) / 2)
    run.font.bold = style["bold"] or None
    run.font.italic = style["italic"] or None
    run.font.color.rgb = RGBColor.from_string(style["color"])
    fonts = run._r.get_or_add_rPr().get_or_add_rFonts()
    name = _word_font_name(style["font"])
    for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attribute), name)


def _word_font_name(pdf_font):
    base = pdf_font.split("+")[-1].split("-")[0].split(",")[0]
    return WORD_FONT_NAMES.get(base, base)


def _add_background(paragraph, background, page_rect):
    width, height = Pt(page_rect.width), Pt(page_rect.height)
    run = paragraph.add_run()
    image = io.BytesIO(background.tobytes("png"))
    inline = run.add_picture(image, width=Emu(width), height=Emu(height))._inline
    anchor = parse_xml(
        f'<wp:anchor {nsdecls("wp")} distT="0" distB="0" distL="0" distR="0" '
        'simplePos="0" relativeHeight="1" behindDoc="1" locked="0" '
        'layoutInCell="1" allowOverlap="1">'
        '<wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>'
        '<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>'
        f'<wp:extent cx="{int(width)}" cy="{int(height)}"/>'
        "<wp:wrapNone/></wp:anchor>"
    )
    for child in inline:
        if child.tag in (qn("wp:docPr"), qn("wp:cNvGraphicFramePr"), qn("a:graphic")):
            anchor.append(copy.deepcopy(child))
    inline.getparent().replace(inline, anchor)
