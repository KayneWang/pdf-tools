# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PDF 工具集：两项功能，提取图片（PyMuPDF/`fitz`）和转 Word（`pdf2docx`）。用户交互文案全部为中文。术语见 `GLOSSARY.md`。

## Commands

```bash
pip install -r requirements.txt          # 安装依赖（pymupdf, pdf2docx, python-docx, pytest）

python -m pytest tests/ -v               # 全量测试（裸 pytest 也可以，见下）
python -m pytest tests/test_cli.py::test_menu_extracts_images_with_defaults -v   # 单个测试

python pdf extract-images input.pdf -o output_dir/   # 子命令模式：提取图片
python pdf to-word input.pdf -o output.docx          # 子命令模式：转 Word（--force 覆盖已有文件，--layout fixed 固定版式）
python pdf                                            # 交互式菜单模式运行
```

## Architecture

- **`pdf`**（无扩展名，项目根目录）：唯一 CLI 入口，双模式分发——`main()` 按 `len(sys.argv) > 1` 判断：有参数走 argparse 子命令，无参数走 `run_menu()`。菜单由 `FEATURES` 注册表（`Feature(功能名, 函数, 默认输出, 输出提示, 询问额外选项的函数)`）渲染。新增功能要往注册表加条目，并在 `SUBCOMMANDS` 和 `build_parser()` 中加子命令。两种模式最终都收敛到 `run_extract()` / `run_to_word()`。
- **`extractor.py`**：核心逻辑 `extract_images(pdf_path, output_dir) -> list[str]`，与 CLI 完全解耦、不感知参数解析。新功能应遵循同样的分层：核心函数放独立模块，`pdf` 只做编排。
- **`converter.py`**：核心逻辑 `convert_to_word(pdf_path, output_path, layout)` 和 `has_editable_text(pdf_path)`。转换全有或全无：先写到输出目录下的临时目录，成功后再替换目标文件。流式版式用 `pdf2docx`，它必须延迟加载（会带来 OpenCV），并且调用时要传 `ignore_page_error=False`（否则会静默丢页）、屏蔽它的日志。是否允许覆盖由 `pdf` 判断，不在核心函数里。
- **`fixed_layout.py`**：固定版式 `write_fixed_layout(pdf_path, output_path)`，只由 `converter.py` 调用。每条视觉行是一个段落，靠缩进、固定行高、段前距和制表位定位；非文字内容渲染成一张透明底图放在文字下方。文字必须和底图对齐，所以行不能折行（负右缩进），否则后面的内容会整体错位。
- **测试分层**：`tests/test_extractor.py`、`tests/test_converter.py`、`tests/test_fixed_layout.py` 直接调核心函数；`tests/test_cli.py` 用 `subprocess` 端到端跑真实 CLI 进程（含通过 stdin 模拟菜单交互）。它们共用 `tests/pdf_fixtures.py`——运行时用 PyMuPDF 现场构造 PDF，仓库不存任何二进制测试文件。

## Conventions & Constraints

- **CLI 文案是契约**：所有提示/错误字符串（`未找到图片`、`错误：输入文件不存在: {path}` 等）被测试逐字断言，改动文案必须同步改测试。
- **错误约定**：错误信息到 stderr 且非 0 退出；PDF 无图片不算错误（stdout 打印 `未找到图片`，exit 0）；扫描件转 Word 不算错误（stderr 打印警告，exit 0）；Ctrl+C 退出码 130；菜单错误不重试，出错即退出。
- **版式效果不能只靠测试判断**：结构断言抓不到文字和底图错位，改 `fixed_layout.py` 后要渲染出来和原 PDF 对比（`qlmanage -t` 可预览，但不等于 Word 的实际效果）。
- **不要把真实文档放进测试或提交**：测试一律用 `tests/pdf_fixtures.py` 现场生成的合成 PDF。
- **PyMuPDF 不能升到 2.x**：`requirements.txt` 固定 `<2`。2.x 弃用 `fitz` 并发出 `FutureWarning`，会违反零警告约定；`pdf2docx` 也依赖 `fitz`。
- **测试输出必须零警告**：`pytest.ini` 按消息精确过滤 PyMuPDF SWIG 的 DeprecationWarning，不要放宽为全局 ignore。
- **根目录空 `conftest.py` 有用途**：让裸 `pytest` 也能把项目根加进 `sys.path`（否则 `from extractor import ...` 会挂），不要删。
- **`docs/superpowers/`** 是本地设计文档/计划（specs、plans），已被 gitignore，不进版本库。
