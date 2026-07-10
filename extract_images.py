"""CLI for extracting embedded images from a PDF file."""
import argparse
import os
import sys

from extractor import extract_images


def main():
    parser = argparse.ArgumentParser(
        description="Extract embedded images from a PDF file."
    )
    parser.add_argument("input", help="Path to the input PDF file")
    parser.add_argument(
        "-o", "--output", help="Output directory for extracted images"
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"错误：输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output
    if not output_dir:
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        output_dir = f"{base_name}_images"

    try:
        saved_paths = extract_images(args.input, output_dir)
    except Exception as e:
        print(f"错误：无法处理PDF文件: {e}", file=sys.stderr)
        sys.exit(1)

    if not saved_paths:
        print("未找到图片")
    else:
        print(f"提取到 {len(saved_paths)} 张图片，已保存到: {output_dir}")


if __name__ == "__main__":
    main()
