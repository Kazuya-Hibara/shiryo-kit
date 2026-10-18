#!/usr/bin/env python3
"""shiryo-kit: HTML デッキから、頼まれた形式の成果物を書き出す（入口はこれ 1 本）。

使い方:
  python3 build.py deck.html                                  # pptx・pdf・読み原稿をすべて
  python3 build.py deck.html --out 出力フォルダ --formats pptx,pdf,notes
  python3 build.py deck.html --formats notes                  # 読み原稿（Markdown）だけ（Node・Chrome 不要）
  python3 build.py deck.html --author "山田 花子"              # pptx の作成者欄（省略時は空）
  python3 build.py deck.html --notes notes.json               # HTML のノートの代わりに JSON を使う
  python3 build.py deck.html --ledger ledger.md               # 書き出しの記録に入れる台帳（省略時は deck.html の隣の ledger.md）
  python3 build.py handout.html --out out --handout           # 配布物（配布 1 枚など）も同じ out/ と書き出しの記録に入れる
  python3 build.py deck.html --unreviewed                     # 未検品で渡す時: file 名と中身（各スライドの右上・文書のプロパティ）に「未検品」
  python3 build.py deck.html --engine python                  # Chrome を使わない予備の書き出し（既定 auto = Chrome が動かなければ自動でこちら）

出力（--out 省略時は deck.html と同じフォルダ）:
  <名前>.pptx           編集できる PowerPoint（本文はテキストボックス・表は PowerPoint の表・ノート付き）
  <名前>.pdf            Chrome の印刷で作る PDF（読み原稿は印刷しない）
  <名前>_読み原稿.md     スライドごとの読み原稿
  manifest.json         書き出しの記録（元の deck.html・ledger.md・BRIEF.md と、書き出した file の sha256・書き出しの方法。check.py manifest が読む）

書き出しの方法（--engine）:
  auto（既定）  Chrome が動けば Chrome で描いてから組み立てる。動かない時（Chrome が無い・Claude や ChatGPT のアプリの中・
                Codex の囲いの中など）は、Python だけの予備の書き出しに自動で切り替え、理由を表示する
  chrome        Chrome だけ（動かなければ止まる）
  python        予備の書き出しだけ（html_to_pptx_static.py）。PDF は LibreOffice があれば pptx から作る（無い・止まる時は作らない）
  予備の書き出しは「描画の確認ができていない書き出し」。manifest.json に export_mode=python-fallback と記録する

notes.json の形: ["1枚目のノート", "", "3枚目…"] か {"1": "…", "3": "…"}（キーはスライド番号）。
依存: pptx = Python の python-pptx・lxml + Node.js 22 以上 + Chrome（または Edge / Chromium）。pdf = Node.js + Chrome。
      予備の書き出し: pptx = python-pptx・lxml だけ。pdf = LibreOffice。notes = 追加の依存なし。
環境変数: SHIRYO_CHROME_WAIT_MS（ブラウザ起動の待ち時間、既定 45000）、CHROME_PATH（ブラウザの場所を指定）、
          SHIRYO_SOFFICE_TIMEOUT（LibreOffice の時間の上限、既定 180 秒）。
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _deps import BrowserUnavailable, find_chrome, require_node  # noqa: E402
from deck_html import parse_deck  # noqa: E402

FORMATS = ("pptx", "pdf", "notes")
ENGINES = ("auto", "chrome", "python")
UNREVIEWED = "未検品"
FALLBACK_NOTE = ("描画の確認ができていない書き出しです（Chrome が使えないため、予備の書き出しで作りました。"
                 "PowerPoint で開いて、はみ出し・重なりを目で確かめてください）")
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
            paras = t.strip().split("\n")
            # HTML のノートで data-ledger="skip"（架空の例など）にした行は、md でも台帳の照合から外す印を付ける
            led = s.notes_ledger if t == s.notes and len(s.notes_ledger) == len(paras) else paras
            for para, lp in zip(paras, led):
                skip = lp.strip() != para.strip()
                lines.append(para.strip() + (" <!-- ledger:skip -->" if skip else ""))
                lines.append("")
        else:
            lines.append("（読み原稿なし）")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


MANIFEST_SCHEMA = "shiryo-kit/build-manifest/v1"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(p, out_dir):
    try:
        return os.path.relpath(Path(p).resolve(), out_dir.resolve())
    except ValueError:  # Windows で deck と out/ のドライブが違う時は、絶対 path で記録する
        return str(Path(p).resolve())


def write_manifest(out_dir, html, ledger, brief, produced, fmts, handout=False, info=None):
    """out/manifest.json。元の file が変わっていない前の書き出しの行は残す（pptx と pdf を別々に作った時・配布物を足した時）。

    produced = [(形式, path, 方法)]。方法 = chrome / python-fallback / libreoffice（予備の pptx から作った PDF）。"""
    from review_evidence import sha256 as _sha
    mpath = out_dir / "manifest.json"
    src_sha = sha256(html)
    old = {}
    if mpath.exists():
        try:
            old = json.loads(mpath.read_text(encoding="utf-8"))
        except ValueError:
            old = {}
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    old_deck = (old.get("deck") or {}).get("path")
    outputs = {}
    for o in old.get("outputs", []):
        if not isinstance(o, dict) or not (out_dir / o.get("file", "")).exists():
            continue
        sp = o.get("source") or old_deck
        if sp and (out_dir / sp).exists() and _sha(out_dir / sp) == o.get("deck_sha256"):
            outputs[o["file"]] = o
    for fmt, p, mode in produced:
        outputs[p.name] = {"file": p.name, "format": fmt, "sha256": sha256(p), "bytes": p.stat().st_size,
                           "source": _rel(html, out_dir), "deck_sha256": src_sha, "mode": mode, "built_at": now}

    def src(p):
        if p is None or not p.exists():
            return None
        return {"path": _rel(p, out_dir), "sha256": sha256(p)}

    m = {"schema": MANIFEST_SCHEMA, "built_at": now, "formats": fmts}
    if handout:
        m["deck"] = old.get("deck")
        m["ledger"] = old.get("ledger") or src(ledger)
        m["brief"] = old.get("brief") or src(brief)
    else:
        m["deck"], m["ledger"], m["brief"] = src(html), src(ledger), src(brief)
    outs = sorted(outputs.values(), key=lambda o: o["file"])
    # 書き出しの方法は pptx・pdf の行から決める（読み原稿だけなら text）。Chrome で組んだ pptx を LibreOffice で PDF にした物は Chrome の側
    modes = {o.get("mode", "chrome") for o in outs if o.get("format") in ("pptx", "pdf")}
    modes = {"chrome" if md == "libreoffice-from-chrome" else md for md in modes}
    if not modes:
        m["export_mode"] = "python-fallback" if (info or {}).get("engine") == "python" and \
            any(f in fmts for f in ("pptx", "pdf")) else "text"
    else:
        m["export_mode"] = "chrome" if modes <= {"chrome"} else "python-fallback"
    m["render_checked"] = m["export_mode"] == "chrome"
    for k, v in (info or {}).items():
        if v and k != "engine":
            m[k] = v
    if old.get("fallback_reason") and m["export_mode"] != "chrome" and "fallback_reason" not in m:
        m["fallback_reason"] = old["fallback_reason"]
    m["outputs"] = outs
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return mpath, m


STAMP_CSS = ("<style>.shiryo-unreviewed{position:absolute;top:2mm;left:50%;transform:translateX(-50%);"
             "font:700 9pt sans-serif;color:#c00000;border:1px solid #c00000;background:#fff;padding:.3mm 1.5mm;z-index:99}</style>")
STAMP_TAG = re.compile(r'(<section\b[^>]*\bclass="[^"]*\b(?:s|slide)\b[^"]*"[^>]*>)')


def stamp_pptx(path):
    """未検品の印: 各スライドの右上に「未検品」の箱、文書のプロパティ（題名・キーワード・分類）にも入れる。"""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Pt
    prs = Presentation(path)
    for slide in prs.slides:
        w = Pt(46)  # 上の中央（型の見出しの帯は左右に字があるので、そこを避ける）
        tb = slide.shapes.add_textbox(int((prs.slide_width - w) / 2), Pt(5), w, Pt(16))
        tb.name = "Unreviewed"
        tf = tb.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        r = tf.paragraphs[0].add_run()
        r.text = UNREVIEWED
        r.font.size, r.font.bold = Pt(9), True
        r.font.color.rgb = RGBColor(0xC0, 0, 0)
        tb.line.color.rgb = RGBColor(0xC0, 0, 0)
    cp = prs.core_properties
    cp.title = f"【{UNREVIEWED}】{cp.title or ''}"
    cp.keywords = cp.category = UNREVIEWED
    prs.save(path)


def build_pdf(html, out_pdf, stamp=False):
    node = require_node()
    src = Path(html).resolve()
    tmp = None
    if stamp:  # 印を足した写しを同じフォルダに作る（画像などの相対 path を保つ）。元の deck.html は変えない
        tmp = src.with_name(f".{src.stem}_{UNREVIEWED}_tmp.html")
        text = src.read_text(encoding="utf-8")
        text = STAMP_TAG.sub(lambda m: m.group(1) + f'<div class="shiryo-unreviewed">{UNREVIEWED}</div>', text)
        tmp.write_text(text.replace("</head>", STAMP_CSS + "</head>", 1) if "</head>" in text else STAMP_CSS + text,
                       encoding="utf-8")
    try:
        r = subprocess.run([node, str(HERE / "html_pdf.mjs"), str(tmp or src), str(out_pdf)],
                           capture_output=True, text=True, encoding="utf-8", timeout=900)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    if r.returncode == 3:  # ブラウザを起動・接続できない
        raise BrowserUnavailable(f"Chrome を起動できない: {r.stderr.strip()[-1500:]}")
    if r.returncode != 0:
        sys.exit(f"PDF の書き出しに失敗: {r.stderr.strip()[-1500:]}")


def chrome_usable():
    """(True, None) か (False, 理由)。Chrome が見つかっても囲いの中では起動しないことがある（それは書き出しの失敗で分かる）。"""
    try:
        require_node()
    except BrowserUnavailable as e:
        return False, str(e).split("\n")[0]
    path, err = find_chrome()
    if not path:
        return False, "Chrome（または Edge / Chromium）が見つからない"
    return True, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", help="HTML デッキ")
    ap.add_argument("--out", help="出力フォルダ（省略時は HTML と同じ場所）")
    ap.add_argument("--formats", default="pptx,pdf,notes", help="pptx,pdf,notes から必要なものをカンマ区切りで")
    ap.add_argument("--author", default="", help="pptx の作成者・最終更新者（省略時は空）")
    ap.add_argument("--notes", help="ノートを JSON で渡す（HTML のノートより優先）")
    ap.add_argument("--ledger", help="書き出しの記録に入れる出典台帳（省略時は deck.html の隣の ledger.md）")
    ap.add_argument("--engine", default="auto", choices=ENGINES, help="auto（既定）/ chrome / python（予備の書き出し）")
    ap.add_argument("--handout", action="store_true", help="配布物として書き出す（記録の元の deck は変えず、配布物の行を足す）")
    ap.add_argument("--unreviewed", action="store_true", help="未検品で渡す: file 名と中身に「未検品」の印を入れる")
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
    if a.handout and not (out_dir / "manifest.json").exists():
        sys.exit("--handout は、先に本体の deck を同じ --out に書き出してから使う（書き出しの記録に本体の deck が要る）")
    mark = f"_{UNREVIEWED}" if a.unreviewed else ""
    stem = html.stem

    deck = parse_deck(html)
    if not deck.slides:
        sys.exit("スライドが見つかりません。1 枚ごとに <section class=\"s\"> … </section> で囲んでください（references/html-contract.md）。")
    notes = load_notes_json(a.notes, len(deck.slides)) if a.notes else [s.notes for s in deck.slides]

    ledger = Path(a.ledger) if a.ledger else html.resolve().parent / "ledger.md"
    if a.ledger and not ledger.exists():
        sys.exit(f"--ledger の file が見つかりません: {ledger}")

    engine, reason = a.engine, ("--engine python で指定" if a.engine == "python" else None)
    if engine == "auto" and ("pptx" in fmts or "pdf" in fmts):
        ok, why = chrome_usable()
        engine, reason = ("chrome", None) if ok else ("python", why)

    done, produced = [], []
    if "notes" in fmts:
        p = out_dir / f"{stem}_読み原稿{mark}.md"
        p.write_text(notes_markdown(deck, notes), encoding="utf-8")
        produced.append(("notes", p, "text"))
        done.append(f"読み原稿: {p}（ノートあり {sum(1 for t in notes if t.strip())}/{len(deck.slides)} 枚）")
    pptx_path = out_dir / f"{stem}{mark}.pptx"
    if "pptx" in fmts and engine == "chrome":
        from html_to_pptx import convert  # python-pptx が無ければここで入れ方を表示して止まる
        try:
            n, n_notes = convert(str(html), str(pptx_path), notes=notes, author=a.author)
            produced.append(("pptx", pptx_path, "chrome"))
            done.append(f"pptx: {pptx_path}（{n} 枚・ノート {n_notes} 枚）")
        except BrowserUnavailable as e:  # 描画の失敗（HTML の誤り・時間切れ）では切り替えない。そのまま止まる
            if a.engine != "auto":
                raise
            engine, reason = "python", f"Chrome を起動できなかった（{str(e).strip()[-300:]}）"
    if "pptx" in fmts and engine == "python":
        from html_to_pptx_static import convert as convert_static
        n, n_notes, over, dropped = convert_static(str(html), str(pptx_path), notes=notes, author=a.author)
        produced.append(("pptx", pptx_path, "python-fallback"))
        done.append(f"pptx: {pptx_path}（{n} 枚・ノート {n_notes} 枚・予備の書き出し）")
        if over:
            done.append(f"注意: {', '.join(f'p{i}' for i in over)} は字を小さくしても枠に収まりきらない（中身を減らすか 2 枚に分ける）")
        if dropped:
            done.append("注意: 予備の書き出しでは、次の枚の画像・図が入っていない（図は中の文字だけ。ロゴ・グラフは PowerPoint で"
                        "貼り直すか、Chrome のある環境で書き出し直す）: " + "・".join(f"p{i}（{k} 個）" for i, k in dropped.items()))
    if "pptx" in fmts and a.unreviewed:
        stamp_pptx(pptx_path)
        produced = [(f, p, m) for f, p, m in produced if p != pptx_path] + [
            next((f, p, m) for f, p, m in produced if p == pptx_path)]
    if "pdf" in fmts:
        p = out_dir / f"{stem}{mark}.pdf"
        if engine == "chrome":
            try:
                build_pdf(html, p, stamp=a.unreviewed)
                produced.append(("pdf", p, "chrome"))
                done.append(f"pdf: {p}")
            except BrowserUnavailable as e:
                if a.engine != "auto":
                    raise
                engine, reason = "python", reason or f"Chrome を起動できなかった（{str(e).strip()[-300:]}）"
        if engine == "python":
            import tempfile
            from office_pdf import pptx_to_pdf
            with tempfile.TemporaryDirectory() as td:
                src = pptx_path if pptx_path.exists() and any(q == pptx_path for _, q, _ in produced) else None
                if src is None:
                    from html_to_pptx_static import convert as convert_static
                    src = Path(td) / f"{stem}{mark}.pptx"
                    convert_static(str(html), str(src), notes=notes, author=a.author)
                    if a.unreviewed:
                        stamp_pptx(src)
                ok, why = pptx_to_pdf(src, p)
            if ok:
                from_chrome = any(q == src and md == "chrome" for _, q, md in produced)
                produced.append(("pdf", p, "libreoffice-from-chrome" if from_chrome else "libreoffice"))
                done.append(f"pdf: {p}（{'Chrome で組んだ' if from_chrome else '予備の'} pptx から LibreOffice で作成）")
            else:
                if p.exists():
                    p.unlink()
                done.append(f"PDF は作れませんでした: {why}。pptx を PowerPoint などで開いて PDF に保存するか、"
                            "Chrome のある環境で書き出し直してください")
    info = {"engine": engine, "fallback_reason": reason if engine == "python" else None,
            "unreviewed_mark": a.unreviewed or None}
    mpath, m = write_manifest(out_dir, html, ledger, html.resolve().parent / "BRIEF.md", produced, fmts,
                              handout=a.handout, info=info)
    done.append(f"書き出しの記録: {mpath}（書き出しの方法: {m['export_mode']}）")
    for d in done:
        print(d)
    if m["export_mode"] == "python-fallback":
        print(f"注意: {FALLBACK_NOTE}")
        if reason:
            print(f"  予備に切り替えた理由: {reason}")
    if any(f == "pptx" for f, _, _ in produced):
        # Chrome が使えなければ check.py pptx が自分で静的な比較に切り替える（--static は付けなくてよい）
        print(f"次: python3 {HERE / 'check.py'} pptx {pptx_path} {html}")


if __name__ == "__main__":
    main()
