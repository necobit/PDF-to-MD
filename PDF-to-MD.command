#!/bin/zsh
# PDF to Markdown GUI 起動スクリプト
# Finderでダブルクリック、またはターミナルから ./PDF-to-MD.command で起動

cd "$(dirname "$0")"

# 仮想環境がなければ自動セットアップ
if [ ! -x .venv/bin/python ]; then
    echo "初回セットアップ中（仮想環境を作成しています）..."
    python3 -m venv .venv || { echo "python3 が見つかりません"; read -k1 "?キーを押して終了"; exit 1; }
    .venv/bin/pip install -r requirements.txt || { echo "依存パッケージのインストールに失敗しました"; read -k1 "?キーを押して終了"; exit 1; }
fi

exec .venv/bin/python pdf2md_gui.py
