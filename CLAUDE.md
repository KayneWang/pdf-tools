# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PDF 工具集：目前唯一功能是从 PDF 中提取内嵌图片（PyMuPDF/`fitz`）。用户交互文案全部为中文。

## Commands

```bash
pip install -r requirements.txt          # 安装依赖（pymupdf, pytest）

python -m pytest tests/ -v               # 全量测试（裸 pytest 也可以，见下）
python -m pytest tests/test_cli.py::test_menu_extracts_images_with_defaults -v   # 单个测试

python pdf input.pdf -o output_dir/      # 参数模式运行
python pdf                                # 交互式菜单模式运行
```

## Architecture

- **`pdf`**（无扩展名，项目根目录）：唯一 CLI 入口，双模式分发——`main()` 按 `len(sys.argv) > 1` 判断：有参数走 argparse，无参数走 `run_menu()`。菜单由 `FEATURES` 注册表（`[(功能名, 函数)]`）渲染，新增功能往注册表里加条目即可。两种模式最终都收敛到 `run_extract()`。
- **`extractor.py`**：核心逻辑 `extract_images(pdf_path, output_dir) -> list[str]`，与 CLI 完全解耦、不感知参数解析，是唯一做实际 PDF 操作的地方。新功能应遵循同样的分层：核心函数放独立模块，`pdf` 只做编排。
- **测试分层**：`tests/test_extractor.py` 直接调核心函数；`tests/test_cli.py` 用 `subprocess` 端到端跑真实 CLI 进程（含通过 stdin 模拟菜单交互）。两者共用 `tests/pdf_fixtures.py`——运行时用 PyMuPDF 现场构造含真实内嵌图片的 PDF，仓库不存任何二进制测试文件。

## Conventions & Constraints

- **CLI 文案是契约**：所有提示/错误字符串（`未找到图片`、`错误：输入文件不存在: {path}` 等）被测试逐字断言，改动文案必须同步改测试。
- **错误约定**：错误信息到 stderr 且非 0 退出；PDF 无图片不算错误（stdout 打印 `未找到图片`，exit 0）；Ctrl+C 退出码 130；菜单错误不重试，出错即退出。
- **测试输出必须零警告**：`pytest.ini` 按消息精确过滤 PyMuPDF SWIG 的 DeprecationWarning，不要放宽为全局 ignore。
- **根目录空 `conftest.py` 有用途**：让裸 `pytest` 也能把项目根加进 `sys.path`（否则 `from extractor import ...` 会挂），不要删。
- **`docs/superpowers/`** 是本地设计文档/计划（specs、plans），已被 gitignore，不进版本库。
