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


def _solid_png(color=(60, 110, 200)):
    """An 80x80 PNG, large enough for layout analysis to keep it as an image."""
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 80), False)
    pixmap.set_rect(pixmap.irect, color)
    return pixmap.tobytes("png")


def make_document_pdf(path):
    """Create a PDF at `path` with Chinese text, a 2x2 ruled table and an image."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "第一章 概述", fontname="china-s", fontsize=20)
    page.insert_text(
        (72, 110), "这是一段中文正文。", fontname="china-s", fontsize=12
    )

    left, top, cell_width, cell_height = 72, 150, 120, 30
    shape = page.new_shape()
    for row in range(3):
        y = top + row * cell_height
        shape.draw_line((left, y), (left + 2 * cell_width, y))
    for column in range(3):
        x = left + column * cell_width
        shape.draw_line((x, top), (x, top + 2 * cell_height))
    shape.finish(color=(0, 0, 0), width=1)
    shape.commit()
    for row, values in enumerate([("姓名", "年龄"), ("张三", "30")]):
        for column, value in enumerate(values):
            page.insert_text(
                (left + column * cell_width + 6, top + row * cell_height + 20),
                value,
                fontname="china-s",
                fontsize=12,
            )

    page.insert_image(fitz.Rect(72, 260, 232, 420), stream=_solid_png())
    doc.save(str(path))
    doc.close()


def make_form_filled_pdf(path):
    """Create a filled-in form: fields overlay blanks in the body text as separate
    objects, with drawn underlines, a stamp over the signature and hidden white text.

    Reading it visually gives the lines in FORM_FILLED_LINES.
    """
    doc = fitz.open()
    page = doc.new_page()

    def text(x, y, value, **kwargs):
        page.insert_text((x, y), value, fontname="china-s", fontsize=12, **kwargs)

    def underline(x0, x1, y):
        page.draw_line((x0, y), (x1, y), color=(0, 0, 0), width=0.5)

    page.insert_text((266, 130), "证明文件", fontname="china-s", fontsize=16)

    text(114, 180, "兹证明")
    text(250, 180, "（编号：")
    text(447, 180, "）任职于")
    text(183, 178, "张三")
    text(332, 178, "A-1024")
    underline(150, 252, 184)
    underline(315, 447, 184)

    text(90, 212, "本公司")
    text(240, 212, "岗位，特此证明。")
    text(143, 210, "工程师")
    underline(130, 238, 216)

    # A pale stamp, on which white text can't be read.
    page.insert_image(fitz.Rect(381, 439, 504, 562), stream=_solid_png((255, 225, 225)))
    text(361, 492, "某某有限公司")
    text(417, 502, "隐藏内容", color=(1, 1, 1))
    text(425, 525, "二〇二〇年")
    doc.save(str(path))
    doc.close()


FORM_FILLED_LINES = [
    "证明文件",
    "兹证明张三（编号：A-1024）任职于",
    "本公司工程师岗位，特此证明。",
    "某某有限公司",
    "二〇二〇年",
]


def make_multi_page_text_pdf(path, page_count):
    """Create a PDF at `path` whose page N contains the text `第N页内容`."""
    doc = fitz.open()
    for number in range(1, page_count + 1):
        doc.new_page().insert_text(
            (72, 72), f"第{number}页内容", fontname="china-s", fontsize=14
        )
    doc.save(str(path))
    doc.close()


def make_scanned_pdf(path):
    """Create a PDF at `path` whose only page is a full-page image, without text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(page.rect, stream=_solid_png())
    doc.save(str(path))
    doc.close()


def make_encrypted_pdf(path):
    """Create a PDF at `path` that needs a password to open."""
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "secret")
    doc.save(
        str(path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="user",
        owner_pw="owner",
    )
    doc.close()


def make_empty_pdf(path):
    """Create a single-page PDF at `path` with no embedded images."""
    doc = fitz.open()
    doc.new_page()
    doc.save(str(path))
    doc.close()
