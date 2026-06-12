#!/usr/bin/env python3
"""PDFをMarkdownに変換するGUIアプリ。

起動: python pdf2md_gui.py
PDFファイルをウィンドウにドラッグ&ドロップするか、「ファイルを選択」で追加し、
「変換」ボタンを押すとMarkdownに変換される。
"""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from pdf2md import convert


class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF to Markdown")
        self.geometry("560x520")
        self.minsize(480, 420)

        self.files: list[Path] = []
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.converting = False

        self._build_ui()
        self.after(100, self._poll_log)

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ドロップゾーン兼ファイルリスト
        frame = ttk.LabelFrame(self, text="PDFファイル（ここにドラッグ&ドロップ）")
        frame.pack(fill="both", expand=True, **pad)

        self.listbox = tk.Listbox(frame, selectmode="extended", height=8)
        self.listbox.pack(fill="both", expand=True, padx=8, pady=8)
        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind("<<Drop>>", self._on_drop)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="ファイルを選択...", command=self._pick_files).pack(side="left")
        ttk.Button(btn_row, text="選択を削除", command=self._remove_selected).pack(side="left", padx=6)
        ttk.Button(btn_row, text="すべてクリア", command=self._clear_files).pack(side="left")

        # オプション
        opts = ttk.LabelFrame(self, text="オプション")
        opts.pack(fill="x", **pad)

        self.var_images = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="画像を抽出する（images/ フォルダに保存）",
                        variable=self.var_images).pack(anchor="w", padx=8, pady=4)

        self.var_no_ocr = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="OCRを使わない（変換結果に謎の文字が混入する場合に）",
                        variable=self.var_no_ocr).pack(anchor="w", padx=8, pady=(0, 4))

        out_row = ttk.Frame(opts)
        out_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Label(out_row, text="出力先:").pack(side="left")
        self.var_outdir = tk.StringVar(value="")
        self.out_entry = ttk.Entry(out_row, textvariable=self.var_outdir)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(out_row, text="参照...", command=self._pick_outdir).pack(side="left")
        ttk.Label(opts, text="※ 出力先が空欄の場合はPDFと同じフォルダに出力します",
                  foreground="gray").pack(anchor="w", padx=8, pady=(0, 6))

        # 変換ボタンと進捗
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", **pad)
        self.convert_btn = ttk.Button(bottom, text="変換", command=self._start_convert)
        self.convert_btn.pack(side="left")
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=8)

        # ログ
        self.log = tk.Text(self, height=7, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # --- ファイル管理 ---

    def _add_files(self, paths):
        for p in paths:
            path = Path(p)
            if path.is_dir():
                self._add_files(sorted(path.glob("*.pdf")) + sorted(path.glob("*.PDF")))
            elif path.suffix.lower() == ".pdf" and path not in self.files:
                self.files.append(path)
                self.listbox.insert("end", str(path))

    def _on_drop(self, event):
        self._add_files(self.tk.splitlist(event.data))

    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="PDFファイルを選択", filetypes=[("PDFファイル", "*.pdf")])
        self._add_files(paths)

    def _remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)
            del self.files[i]

    def _clear_files(self):
        self.listbox.delete(0, "end")
        self.files.clear()

    def _pick_outdir(self):
        d = filedialog.askdirectory(title="出力先フォルダを選択")
        if d:
            self.var_outdir.set(d)

    # --- 変換 ---

    def _start_convert(self):
        if self.converting:
            return
        if not self.files:
            self._log_msg("PDFファイルを追加してください")
            return
        self.converting = True
        self.convert_btn.config(state="disabled")
        self.progress.config(maximum=len(self.files), value=0)
        outdir = self.var_outdir.get().strip()
        threading.Thread(
            target=self._convert_worker,
            args=(list(self.files), Path(outdir) if outdir else None,
                  self.var_images.get(), not self.var_no_ocr.get()),
            daemon=True,
        ).start()

    def _convert_worker(self, files: list[Path], outdir: Path | None, images: bool, ocr: bool):
        ok = 0
        for pdf in files:
            out_path = (outdir or pdf.parent) / f"{pdf.stem}.md"
            try:
                convert(pdf, out_path, images=images, pages=None, ocr=ocr)
                self.log_queue.put(f"✓ {pdf.name} → {out_path}")
                ok += 1
            except Exception as e:
                self.log_queue.put(f"✗ {pdf.name}: {e}")
            self.log_queue.put("__PROGRESS__")
        self.log_queue.put(f"完了: {ok}/{len(files)} 件成功")
        self.log_queue.put("__DONE__")

    # --- ログ表示（ワーカースレッドからUIを直接触らない） ---

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "__DONE__":
                    self.converting = False
                    self.convert_btn.config(state="normal")
                elif msg == "__PROGRESS__":
                    self.progress.step(1)
                else:
                    self._log_msg(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def _log_msg(self, msg: str):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()
