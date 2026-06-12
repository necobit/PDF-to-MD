#!/usr/bin/env python3
"""PDFをMarkdownに変換するツール。

使い方:
    python pdf2md.py input.pdf                  # input.md を同じ場所に出力
    python pdf2md.py input.pdf -o out.md        # 出力先を指定
    python pdf2md.py ./pdfs/ -o ./output/       # フォルダ内のPDFを一括変換
    python pdf2md.py input.pdf --images         # 画像も抽出して images/ に保存
    python pdf2md.py input.pdf --pages 1-5,8    # ページ範囲を指定
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import pymupdf
import pymupdf4llm
from pymupdf4llm.helpers import utils as _pymupdf4llm_utils


def _expand_pictures(page) -> None:
    """レイアウトモデルが検出したpicture範囲を、つながったベクター線画まで広げる。

    pymupdf4llm 1.27のレイアウト検出は回路図などの線画の範囲を小さく見積もり、
    抽出画像が切り取られることがある（上流バグの回避策）。
    """
    table_boxes = [pymupdf.Rect(b[:4]) for b in page.layout_information if b[4] == "table"]
    rects = []
    for d in page.get_drawings():
        r = d["rect"]
        # 空、ページ幅いっぱいの罫線・下線、表の枠線は対象外
        if r.is_empty or r.width > page.rect.width * 0.8:
            continue
        if any(r.intersects(t) for t in table_boxes):
            continue
        rects.append(r)

    max_area = abs(page.rect) * 0.6
    for i, box in enumerate(page.layout_information):
        if box[4] != "picture":
            continue
        grown = pymupdf.Rect(box[:4])
        changed = True
        while changed:
            changed = False
            for r in rects:
                if r.intersects(grown) and not (grown.x0 <= r.x0 and grown.y0 <= r.y0
                                                and grown.x1 >= r.x1 and grown.y1 >= r.y1):
                    grown |= r
                    changed = True
        if abs(grown) <= max_area:
            page.layout_information[i] = list(grown) + [box[4]]


_orig_clean_pictures = _pymupdf4llm_utils.clean_pictures


def _clean_pictures_patched(page, blocks):
    _orig_clean_pictures(page, blocks)
    _expand_pictures(page)


_pymupdf4llm_utils.clean_pictures = _clean_pictures_patched


def parse_pages(spec: str) -> list[int]:
    """"1-5,8" のようなページ指定を0始まりのページ番号リストに変換する。"""
    pages: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start) - 1, int(end)))
        else:
            pages.append(int(part) - 1)
    return pages


def convert(pdf_path: Path, out_path: Path, *, images: bool, pages: list[int] | None,
            ocr: bool = True) -> None:
    kwargs: dict = {"use_ocr": ocr}
    if pages is not None:
        kwargs["pages"] = pages
    if images:
        image_dir = out_path.parent / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        kwargs.update(
            write_images=True,
            image_path=str(image_dir),
            image_format="png",
        )

    md_text = pymupdf4llm.to_markdown(str(pdf_path), **kwargs)
    if images:
        # pymupdf4llmの画像リンクはカレントディレクトリ基準のパスになるため、
        # 実在ファイルをファイル名で照合して出力先からの相対パスに書き直す
        def _relink(m: re.Match) -> str:
            name = m.group(1).rsplit("/", 1)[-1]
            if (image_dir / unquote(name)).exists():
                return f"](images/{name})"
            return m.group(0)
        md_text = re.sub(r"\]\(([^)]+?\.png)\)", _relink, md_text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md_text, encoding="utf-8")
    print(f"✓ {pdf_path.name} → {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PDFをMarkdownに変換する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("使い方:")[1],
    )
    parser.add_argument("input", type=Path, help="PDFファイル、またはPDFが入ったフォルダ")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="出力先（.mdファイル、またはフォルダ）")
    parser.add_argument("--images", action="store_true",
                        help="画像を抽出して images/ フォルダに保存し、Markdownからリンクする")
    parser.add_argument("--pages", type=str, default=None,
                        help="変換するページ（例: 1-5,8,10-12）。省略時は全ページ")
    parser.add_argument("--no-ocr", action="store_true",
                        help="OCRを無効にする（テキスト層のあるPDFで謎文字が混入する場合に）")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"エラー: {args.input} が見つかりません", file=sys.stderr)
        return 1

    pages = parse_pages(args.pages) if args.pages else None

    if args.input.is_dir():
        pdfs = sorted(args.input.glob("*.pdf")) + sorted(args.input.glob("*.PDF"))
        if not pdfs:
            print(f"エラー: {args.input} にPDFファイルがありません", file=sys.stderr)
            return 1
        out_dir = args.output or args.input
        failed = 0
        for pdf in pdfs:
            try:
                convert(pdf, out_dir / f"{pdf.stem}.md", images=args.images, pages=pages,
                        ocr=not args.no_ocr)
            except Exception as e:
                print(f"✗ {pdf.name}: {e}", file=sys.stderr)
                failed += 1
        print(f"\n完了: {len(pdfs) - failed}/{len(pdfs)} 件成功")
        return 1 if failed else 0

    # 単一ファイル
    if args.output and (args.output.is_dir() or args.output.suffix == ""):
        out_path = args.output / f"{args.input.stem}.md"
    else:
        out_path = args.output or args.input.with_suffix(".md")
    try:
        convert(args.input, out_path, images=args.images, pages=pages, ocr=not args.no_ocr)
    except Exception as e:
        print(f"✗ 変換失敗: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
