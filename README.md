# pdf-tools

## 图片提取

从 PDF 文件中提取内嵌图片。

```bash
python pdf input.pdf -o output_dir/
```

- `input.pdf`：待提取图片的 PDF 文件
- `-o/--output`：图片输出目录（可选，默认 `<pdf文件名>_images/`）

也可以不带参数进入交互式菜单：

```bash
python pdf
```

按提示选择功能、输入 PDF 路径和输出目录（回车使用默认值）即可。
