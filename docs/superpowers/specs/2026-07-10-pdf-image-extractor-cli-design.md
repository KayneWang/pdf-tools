# PDF 图片提取 CLI 工具 — 设计文档

日期：2026-07-10

## 背景 / 目标

在当前空目录 `pdf-tools` 中搭建一个 PDF 工具集项目。第一个功能：从 PDF 文件中提取内嵌图片，以命令行工具（CLI）形式使用。范围明确限定为“图片提取”，不包含合并/拆分、格式转换、压缩、加解密水印等其他 PDF 功能（这些留待后续按需扩展）。

## 技术选型

- 语言：Python
- PDF 处理库：PyMuPDF（`fitz`）—— 对提取内嵌图片支持最好，能保留原始格式与分辨率，优于 `pypdf` / `pdfplumber`
- CLI 参数解析：标准库 `argparse`（无需引入第三方 CLI 框架）

## 用法

```bash
python extract_images.py input.pdf -o output_dir/
```

- `input.pdf`：待提取图片的 PDF 文件（必填，位置参数）
- `-o / --output`：图片输出目录（可选；默认值为 `<pdf文件名(不含扩展名)>_images/`，创建于当前工作目录）

## 架构 / 数据流

1. CLI 入口（`extract_images.py`）解析命令行参数：
   - 校验输入文件存在且扩展名/内容为 PDF
   - 计算/创建输出目录（若不存在则自动创建，包括多级目录）
2. 调用核心函数 `extractor.extract_images(pdf_path, output_dir) -> list[str]`：
   - 用 PyMuPDF 打开 PDF，遍历每一页
   - 对每页调用 `page.get_images(full=True)` 获取该页引用的图片 xref 列表
   - 对每个 xref 调用 `doc.extract_image(xref)` 取出原始图片字节（`image` 字段）和格式（`ext` 字段，如 `png`/`jpeg`）
   - 按 `page{N}_img{M}.{ext}` 命名（N、M 从 1 开始计数），写入输出目录
   - 返回写入的文件路径列表
3. CLI 层根据返回结果打印摘要：
   - 提取到图片：打印数量与保存目录路径
   - 未提取到图片：打印“未找到图片”提示，正常退出（exit code 0）

## 边界情况与错误处理

| 情况 | 处理方式 |
|---|---|
| 输入文件不存在 | 打印错误信息到 stderr，非 0 状态码退出 |
| 输入文件不是合法 PDF（无法被 PyMuPDF 打开） | 捕获异常，打印错误信息到 stderr，非 0 状态码退出 |
| PDF 中没有任何内嵌图片 | 打印提示“未找到图片”，正常退出（exit code 0），不视为错误 |
| 输出目录不存在 | 自动递归创建 |
| 同名图片文件已存在于输出目录 | 直接覆盖（不做额外的去重/追加逻辑，保持简单） |

## 项目结构

```
pdf-tools/
├── extract_images.py     # CLI 入口：argparse 参数解析 + 调用核心逻辑 + 打印结果
├── extractor.py           # 核心函数：extract_images(pdf_path, output_dir) -> list[str]
├── requirements.txt        # pymupdf
└── tests/
    └── test_extractor.py   # 针对 extractor.py 的单元测试
```

`extractor.py` 的核心逻辑与 CLI 参数解析解耦：核心函数只依赖“输入路径 + 输出目录”，不感知命令行参数，便于单独单元测试，也为后续扩展其他 PDF 功能（合并、转换等）预留清晰边界。

## 测试计划

- 为 `extractor.py` 编写单元测试：
  - 使用一个包含已知数量图片的小样本 PDF（测试时生成或存放于 `tests/fixtures/`），验证：
    - 提取到的图片数量与预期一致
    - 图片文件被正确写入指定输出目录
    - 文件名符合 `page{N}_img{M}.{ext}` 规则
  - 使用一个不含图片的 PDF，验证返回空列表
- CLI 层（`extract_images.py`）做手动/集成验证：跑一次真实命令，检查退出码与输出目录内容
