# PDF-to-MD

PDFをMarkdownに変換するツール（GUI / CLI）。[pymupdf4llm](https://pypi.org/project/pymupdf4llm/) を使用し、見出し・表・画像の抽出に対応しています。

## 動作環境

- Python 3.10以上
- GUIの起動スクリプト（`PDF-to-MD.command`）はmacOS用。WindowsやLinuxでも `python pdf2md_gui.py` で起動できます

## セットアップ

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## GUIアプリ

Finderで **PDF-to-MD.command** をダブルクリックすると起動します（初回は仮想環境のセットアップが自動で実行されます）。

ターミナルからの場合:

```bash
./PDF-to-MD.command
# または
.venv/bin/python pdf2md_gui.py
```

1. PDFファイルをウィンドウにドラッグ&ドロップ（または「ファイルを選択...」）。フォルダをドロップすると中のPDFをまとめて追加
2. 必要なら「画像を抽出する」にチェック、出力先フォルダを指定（空欄ならPDFと同じフォルダ）
3. 「変換」ボタンを押すと一括変換され、進捗とログが表示される

## CLIの使い方

```bash
# 単一ファイルを変換（input.md が同じ場所に出力される）
.venv/bin/python pdf2md.py input.pdf

# 出力先を指定
.venv/bin/python pdf2md.py input.pdf -o output.md

# フォルダ内のPDFを一括変換
.venv/bin/python pdf2md.py ./pdfs/ -o ./output/

# 画像も抽出（出力先の images/ フォルダに保存され、Markdownからリンクされる）
.venv/bin/python pdf2md.py input.pdf --images

# ページ範囲を指定して変換
.venv/bin/python pdf2md.py input.pdf --pages 1-5,8

# OCRを無効にして変換
.venv/bin/python pdf2md.py input.pdf --no-ocr
```

## オプション

| オプション | 説明 |
|-----------|------|
| `-o, --output` | 出力先（`.md` ファイル、またはフォルダ） |
| `--images` | 画像をPNGとして抽出し、Markdownからリンクする |
| `--pages` | 変換するページ（例: `1-5,8,10-12`）。省略時は全ページ |
| `--no-ocr` | OCRを無効にする |

### OCRについて

pymupdf4llmは「画像の中に文字がありそう」と判断したページを自動でOCRします。テキスト層が正常なPDFでもロゴ画像などが原因でOCRが誤発動し、変換結果に謎の文字（添字や記号の誤認識）が混入することがあります。その場合は `--no-ocr`（GUIでは「OCRを使わない」チェック）を指定してください。

## ライセンス

このリポジトリのコードは [MIT License](LICENSE) です。

ただし、依存ライブラリの [pymupdf4llm / PyMuPDF](https://pymupdf.readthedocs.io/) は **AGPL-3.0**（または[Artifex商用ライセンス](https://artifex.com/licensing/)）のデュアルライセンスです。個人・社内での利用は問題ありませんが、本ツールを組み込んだ製品の配布やネットワークサービスとしての提供を行う場合は、AGPL-3.0の義務（ソースコード公開等）に従うか、Artifexの商用ライセンスを取得する必要があります。

その他の依存ライブラリ: [tkinterdnd2](https://pypi.org/project/tkinterdnd2/)（MIT）
