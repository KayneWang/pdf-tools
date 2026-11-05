# pdf-tools

PDF 工具集，支持提取图片和转 Word。

```bash
pip install -r requirements.txt
```

## 提取图片

从 PDF 文件中提取内嵌图片。

```bash
python pdf extract-images input.pdf -o output_dir/
```

- `input.pdf`：待提取图片的 PDF 文件
- `-o/--output`：图片输出目录（可选，默认 `<pdf文件名>_images/`）

## 转 Word

将 PDF 转换为可继续编辑、并尽量保留版式的 Word 文档（`.docx`）。

```bash
python pdf to-word input.pdf -o output.docx
```

- `input.pdf`：待转换的 PDF 文件，始终转换整份文档
- `-o/--output`：输出文件路径，必须以 `.docx` 结尾（可选，默认 `<pdf文件名>.docx`）
- `--force`：覆盖已存在的输出文件（默认遇到已存在的文件会报错退出）
- `--layout`：版式，默认 `flow`

| 版式 | 做法 | 适合 | 取舍 |
|---|---|---|---|
| `flow`（流式） | 推断段落、表格和分栏 | 长文档、报告 | 文字可自动换行；排版特殊的文档可能错乱 |
| `fixed`（固定） | 每一行按 PDF 中的位置摆放 | 证明、表单、填写过的文档 | 版式稳定；每行是独立段落，改字后不会自动换行 |

如果转换后格式错乱，可以换成固定版式：

```bash
python pdf to-word input.pdf -o output.docx --layout fixed
```

固定版式中，下划线、表格线、公章和图片会合成一张底图放在文字下方，因此不能单独编辑，移动文字时也不会跟着动。

已知限制：

- **多栏版式：** 使用流式版式时文字会保留，但可能需要手动调整，例如栏尾文字被识别成表格。
- **扫描件：** 不做文字识别，页面以图片形式保留，转换时会给出警告。
- **加密 PDF：** 需要密码才能打开的 PDF 无法转换。

转换是全有或全无的：任何一页失败都会报错退出，不会生成缺页的文档，也不会改动已有的输出文件。

## 交互式菜单

不带参数运行可进入交互式菜单：

```bash
python pdf
```

按提示选择功能、输入 PDF 路径和输出位置（回车使用默认值）即可，转 Word 还会询问版式。菜单中转 Word 不会覆盖已存在的文件，需要覆盖时请使用 `--force`。
