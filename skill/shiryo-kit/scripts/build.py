#!/usr/bin/env python3
"""shiryo-kit: HTML デッキから、頼まれた形式の成果物を書き出す（入口はこれ 1 本）。

使い方:
  python3 build.py deck.html                                  # pptx・pdf・読み原稿をすべて
  python3 build.py deck.html --out 出力フォルダ --formats pptx,pdf,notes
  python3 build.py deck.html --formats notes                  # 読み原稿（Markdown）だけ（Node・Chrome 不要）
  python3 build.py deck.html --author "山田 花子"              # pptx の作成者欄（省略時は空）
  python3 build.py deck.html --notes notes.json               # HTML のノートの代わりに JSON を使う

出力（--out 省略時は deck.html と同じフォルダ）:
  <名前>.pptx           編集できる PowerPoint（本文はテキストボックス・表は PowerPoint の表・ノート付き）
  <名前>.pdf            Chrome の印刷で作る PDF（読み原稿は印刷しない）
  <名前>_読み原稿.md     スライドごとの読み原稿

notes.json の形: ["1枚目のノート", "", "3枚目…"] か {"1": "…", "3": "…"}（キーはスライド番号）。
依存: pptx = Python の python-pptx・lxml + Node.js 22 以上 + Chrome（または Edge / Chromium）。pdf = Node.js + Chrome。
      notes = 追加の依存なし。足りない時は入れ方を表示して止まる。
環境変数: SHIRYO_CHROME_WAIT_MS（ブラウザ起動の待ち時間、既定 45000）、CHROME_PATH（ブラウザの場所を指定）。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _deps import require_node  # noqa: E402
from deck_html import parse_deck  # noqa: E402

FORMATS = ("pptx", "pdf", "notes")
CHARS_PER_MIN = 300  # 読み上げの目安（日本語 1 分 300 字前後）


def load_notes_json(path, n):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    notes = [""] * n
    if isinstance(data, list):
        for i, t in enumerate(data[:n]):
            notes[i] = (t or "").strip()
    elif isinstance(data, dict):
        for k, t in data.items():
            i = int(k) - 1
            if 0 <= i < n:
                notes[i] = (t or "").strip()
    else:
        sys.exit("notes.json はリスト（スライド順）か {\"スライド番号\": \"ノート\"} の形にしてください。")
    return notes


def notes_markdown(deck, notes):
    total = sum(len(t.replace("\n", "")) for t in notes)
    lines = [f"# {deck.title or '資料'} — 読み原稿", "",
             f"スライド {len(deck.slides)} 枚 / 読み原稿 {total} 字（目安 約 {max(1, round(total / CHARS_PER_MIN))} 分・1 分 {CHARS_PER_MIN} 字で計算） <!-- ledger:skip -->", ""]
    for s, t in zip(deck.slides, notes):
        title = s.label or "（タイトルなし）"
        lines.append(f"## {s.index}. {title}")
        lines.append("")
        if t.strip():
            for para in t.strip().split("\n"):
                lines.append(para.strip())
                lines.append("")
        else:
            lines.append("（読み原稿なし）")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_pdf(html, out_pdf):
    node = require_node()
    r = subprocess.run([node, str(HERE / "html_pdf.mjs"), str(Path(html).resolve()), str(out_pdf)],
                       capture_output=True, text=True, encoding="utf-8", timeout=900)
    if r.returncode != 0:
        sys.exit(f"PDF の書き出しに失敗: {r.stderr.strip()[-1500:]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", help="HTML デッキ")
    ap.add_argument("--out", help="出力フォルダ（省略時は HTML と同じ場所）")
    ap.add_argument("--formats", default="pptx,pdf,notes", help="pptx,pdf,notes から必要なものをカンマ区切りで")
    ap.add_argument("--author", default="", help="pptx の作成者・最終更新者（省略時は空）")
    ap.add_argument("--notes", help="ノートを JSON で渡す（HTML のノートより優先）")
    a = ap.parse_args()

    html = Path(a.deck)
    if not html.exists():
        sys.exit(f"HTML が見つかりません: {html}")
    fmts = [f.strip().lower() for f in a.formats.split(",") if f.strip()]
    bad = [f for f in fmts if f not in FORMATS]
    if bad or not fmts:
        sys.exit(f"--formats に使えるのは {', '.join(FORMATS)} です（指定: {a.formats}）")
    out_dir = Path(a.out) if a.out else html.resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = html.stem

    deck = parse_deck(html)
    if not deck.slides:
        sys.exit("スライドが見つかりません。1 枚ごとに <section class=\"s\"> … </section> で囲んでください（references/html-contract.md）。")
    notes = load_notes_json(a.notes, len(deck.slides)) if a.notes else [s.notes for s in deck.slides]

    done = []
    if "notes" in fmts:
        p = out_dir / f"{stem}_読み原稿.md"
        p.write_text(notes_markdown(deck, notes), encoding="utf-8")
        done.append(f"読み原稿: {p}（ノートあり {sum(1 for t in notes if t.strip())}/{len(deck.slides)} 枚）")
    if "pptx" in fmts:
        from html_to_pptx import convert  # python-pptx が無ければここで入れ方を表示して止まる
        p = out_dir / f"{stem}.pptx"
        n, n_notes = convert(str(html), str(p), notes=notes, author=a.author)
        done.append(f"pptx: {p}（{n} 枚・ノート {n_notes} 枚）")
    if "pdf" in fmts:
        p = out_dir / f"{stem}.pdf"
        build_pdf(html, p)
        done.append(f"pdf: {p}")
    for d in done:
        print(d)
    if "pptx" in fmts:
        print(f"次: python3 {HERE / 'check.py'} pptx {out_dir / (stem + '.pptx')} {html}")


if __name__ == "__main__":
    main()
