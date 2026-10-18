#!/usr/bin/env python3
"""shiryo-kit: Chrome を使わない予備の書き出し。HTML デッキを Python（標準ライブラリ + python-pptx）だけで編集できる PPTX にする。

ふだんは build.py が、Chrome が起動しない環境（Claude のアプリ・ChatGPT の Work・Codex の囲いの中など）で自動で使う
（build.py --engine python で明示もできる）。この script を直接呼ぶのは試験の時だけ。

仕組み: HTML と <style> を読み（css_lite.py）、ブラウザの代わりに簡単な組版で位置を決め、html_dump.mjs と同じ形の
描画の記録を作って html_to_pptx.assemble に渡す。
  文字 → テキストボックス（字の大きさ・太字・色・明朝/ゴシックは CSS から）／箇条書き → 箇条書き書式
  表 → PowerPoint の表（結合セル・セルの余白・罫線・塗り）／ノート → PowerPoint のノート
  格子（display:grid）と横並び（display:flex）→ 横に並べた列／背景色のある塊 → 四角形／下線・上線 → 直線
  SVG の図 → 図の中の文字だけを文字の箱にする（図形は描かない）／画像 → 手元にある file なら貼る
限界: ブラウザと同じ見た目にはならない（縦の中央寄せ・CSS の飾り・SVG の図形は再現しない）。描画の確認ができていない
書き出しなので、build.py は manifest.json に export_mode=python-fallback と記録し、利用者にそう伝える。
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import css_lite  # noqa: E402
from deck_html import BLOCK, TITLE_CLASSES, VOID, parse_deck  # noqa: E402
from pptx_metrics import text_em, wrap_lines  # noqa: E402

SLIDE_W, SLIDE_H = 960.0, 540.0  # pt（16:9）
AUTO_CLOSE = {"p", "li", "dt", "dd", "tr", "td", "th", "option"}
SKIP = {"script", "style", "template", "noscript", "head", "title"}
CJK = "　-鿿＀-￯"
NL = "\u0001"
DEFAULT_SIZE = 12.0
MIN_SCALE = 0.55


# ---------------------------------------------------------------- 木
class Node:
    __slots__ = ("tag", "attrs", "classes", "children", "parent", "first", "last", "style", "font")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.classes = set((attrs.get("class") or "").split())
        self.children, self.first, self.last, self.style, self.font = [], None, None, {}, {}

    def elements(self):
        return [c for c in self.children if isinstance(c, Node)]


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag in AUTO_CLOSE and self.stack[-1].tag == tag:
            self.stack.pop()
        if tag in ("td", "th") and self.stack[-1].tag in ("td", "th"):
            self.stack.pop()
        if tag == "tr" and self.stack[-1].tag in ("td", "th"):
            self.stack.pop()
            if self.stack[-1].tag == "tr":
                self.stack.pop()
        n = Node(tag, a, self.stack[-1])
        self.stack[-1].children.append(n)
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _mark_siblings(n):
    els = n.elements()
    for i, c in enumerate(els):
        c.first, c.last = i == 0, i == len(els) - 1
        _mark_siblings(c)


def is_slide(n):
    return (n.tag == "section" and ({"s", "slide"} & n.classes)) or "slide" in n.classes


def find_slides(n, out):
    for c in n.elements():
        if is_slide(c):
            out.append(c)
        else:
            find_slides(c, out)
    return out


# ---------------------------------------------------------------- 書式
def _serif(family):
    f = (family or "").lower()
    if re.search(r"mincho|明朝", f):
        return True
    first = f.split(",")[0].strip().strip("'\"")
    return first == "serif" or (("serif" in first) and "sans" not in first)


class Styler:
    def __init__(self, html):
        self.rules, self.vars = css_lite.parse_css(css_lite.style_text(html))

    def apply(self, n):
        n.style = css_lite.computed(self.rules, self.vars, n)
        p = n.parent.font if n.parent is not None and n.parent.font else {
            "size": DEFAULT_SIZE, "bold": False, "italic": False, "color": "#222222", "serif": False, "lh": 1.5,
            "align": "left"}
        st = n.style
        f = dict(p)
        size = css_lite.length_pt(st.get("font-size"), p["size"])
        if size:
            f["size"] = size
        if n.tag in ("h1", "h2", "h3", "h4", "h5", "h6") and not size:
            f["size"] = p["size"] * {"h1": 2.0, "h2": 1.5, "h3": 1.17}.get(n.tag, 1.0)
        w = st.get("font-weight", "").strip().lower()
        if w:
            f["bold"] = w in ("bold", "bolder") or (w.isdigit() and int(w) >= 600)
        elif n.tag in ("b", "strong", "th", "h1", "h2", "h3", "h4", "h5", "h6"):
            f["bold"] = True
        if st.get("font-style"):
            f["italic"] = "italic" in st["font-style"]
        elif n.tag in ("i", "em"):
            f["italic"] = True
        c = css_lite.color(st.get("color"))
        if c:
            f["color"] = c
        if st.get("font-family"):
            f["serif"] = _serif(st["font-family"])
        lh = st.get("line-height", "").strip()
        if lh:
            try:
                f["lh"] = float(lh)
            except ValueError:
                v = css_lite.length_pt(lh, f["size"])
                f["lh"] = (v / f["size"]) if v else 1.4
        if st.get("text-align") in ("left", "center", "right", "justify", "start", "end"):
            f["align"] = st["text-align"]
        tt = st.get("text-transform", "").strip().lower()
        if tt in ("uppercase", "lowercase", "none"):
            f["tt"] = tt
        n.font = f
        for ch in n.elements():
            self.apply(ch)


def hidden(n):
    return (css_lite.is_hidden(n.style) or "hidden" in n.attrs or n.tag in SKIP
            or (n.tag == "aside" and "notes" in n.classes))


def display(n):
    d = n.style.get("display", "").strip().lower()
    if d:
        return d
    if n.tag in ("table",):
        return "table"
    if n.tag == "li":
        return "list-item"
    return "block" if n.tag in BLOCK else "inline"


def is_block(n, parent_disp=""):
    if parent_disp.startswith(("flex", "grid", "inline-flex", "inline-grid")):
        return True  # flex・grid の子は塊になる
    return display(n) not in ("inline", "inline-block", "contents") or n.tag in ("svg", "img")


def box4(v, base):
    """'4mm 2.5mm' → [上, 右, 下, 左] pt。"""
    parts = (v or "").split()
    vals = [css_lite.length_pt(x, base) or 0.0 for x in parts[:4]] or [0.0]
    if len(vals) == 1:
        vals = vals * 4
    elif len(vals) == 2:
        vals = vals * 2
    elif len(vals) == 3:
        vals = vals + [vals[1]]
    return vals


def side(n, prop, base):
    """padding / margin の各辺（個別指定が後勝ち）。"""
    v = box4(n.style.get(prop), base)
    for i, s in enumerate(("top", "right", "bottom", "left")):
        x = css_lite.length_pt(n.style.get(f"{prop}-{s}"), base)
        if x is not None:
            v[i] = x
    return v


def border(n, s):
    v = n.style.get(f"border-{s}") or n.style.get("border")
    if not v:
        return None
    v = v.strip().lower()
    if v in ("0", "none", "0px", "hidden"):
        return None
    w = next((css_lite.length_pt(t, n.font["size"]) for t in v.split() if css_lite.length_pt(t, n.font["size"])), 1.0)
    c = css_lite.color(v) or "#999999"
    if w <= 0 or "none" in v.split():
        return None
    return {"w": w, "color": c, **({"dash": "dashed"} if "dashed" in v else {"dash": "dotted"} if "dotted" in v else {})}


# ---------------------------------------------------------------- 文字の流れ
def _finish(runs):
    """ソースの改行由来の空白を和文の間では詰め、ほかは 1 つの空白に。"""
    out = []
    for i, r in enumerate(runs):
        t = r["text"]
        prev = out[-1]["text"][-1:] if out and out[-1]["text"] else ""
        nxt = ""
        for rr in runs[i + 1:]:
            if rr["text"]:
                nxt = rr["text"].lstrip(NL + " ")[:1]
                break

        def rep(m, t=t, prev=prev, nxt=nxt):
            a = t[m.start() - 1] if m.start() > 0 else prev
            b = t[m.end()] if m.end() < len(t) else nxt
            if NL in m.group(0) and re.match(f"[{CJK}]", a or "") and re.match(f"[{CJK}]", b or ""):
                return ""
            return " "
        t = re.sub(f"[ {NL}]+", rep, t)
        out.append(dict(r, text=t))
    while out and not out[0]["text"].strip(" "):
        out.pop(0)
    if out:
        out[0]["text"] = out[0]["text"].lstrip(" ")
        out[-1]["text"] = out[-1]["text"].rstrip(" ")
    return [r for r in out if r["text"]]


def run_of(text, f):
    tt = f.get("tt")
    if tt == "uppercase":
        text = text.upper()
    elif tt == "lowercase":
        text = text.lower()
    return {"text": text, "size": f["size"], "bold": f["bold"], "italic": f["italic"], "color": f["color"],
            "serif": f["serif"], "font": ""}


def inline_runs(n, out, parent_disp=""):
    """インラインの中身 → runs（"\\n" の run は改行）。"""
    for c in n.children:
        if isinstance(c, str):
            t = re.sub(r"[ \t\r\f]*\n[ \t\r\f\n]*", NL, c)
            t = re.sub(r"[ \t\r\f]+", " ", t).replace(" ", " ")
            if t:
                out.append(run_of(t, n.font))
        elif c.tag == "br":
            out.append({"text": "\n"})
        elif not hidden(c):
            inline_runs(c, out)
    return out


def split_paras(runs):
    paras, cur = [], []
    for r in runs:
        if r.get("text") == "\n":
            paras.append(cur)
            cur = []
        else:
            cur.append(r)
    paras.append(cur)
    return [p for p in (_finish(p) for p in paras) if p]


def svg_text(n):
    out = []

    def walk(x):
        for c in x.children:
            if isinstance(c, Node):
                if c.tag in ("text", "tspan", "textpath") and not hidden(c):
                    t = re.sub(r"\s+", " ", "".join(s for s in c.children if isinstance(s, str))).strip()
                    if t:
                        out.append(t)
                    walk(c)
                elif not hidden(c):
                    walk(c)
    walk(n)
    return out


# ---------------------------------------------------------------- 組版
class Layout:
    def __init__(self, base_dir, k=1.0):
        self.items, self.k, self.base_dir = [], k, base_dir
        self.dropped = 0  # 入れられなかった画像・図（SVG は中の文字だけにする）

    def fs(self, f):
        return f["size"] * self.k

    # --- 文字の箱
    def text_box(self, paras_runs, x, y, w, f, align=None, bullet=None, role=None):
        if not paras_runs:
            return 0.0
        w = max(w, 24.0)  # 狭すぎる箱でも文字は落とさない（はみ出しは check.py pptx が見る）
        paras, h, lines = [], 0.0, 0
        for runs in paras_runs:
            runs = [dict(r, size=r["size"] * self.k) for r in runs]
            size = max(r["size"] for r in runs)
            lh = size * max(1.0, f["lh"])
            hang = size if bullet else 0
            n = wrap_lines("".join(r["text"] for r in runs), size, w - hang)
            lines += n
            h += n * lh
            p = {"runs": runs, "align": align or f["align"], "lineHeight": lh}
            if bullet:
                p["bullet"] = {"char": bullet, "color": runs[0]["color"], "size": size}
                p["hang"] = hang
            paras.append(p)
        it = {"t": "text", "x": x, "y": y, "w": w, "h": h, "paras": paras, "lines": lines}
        if role:
            it["role"] = role
        self.items.append(it)
        return h

    # --- 塊
    def block(self, n, x, y, w, parent_disp="", role_title=None):
        """n を (x, y) から幅 w で組み、使った高さを返す。"""
        if hidden(n):
            return 0.0
        f = n.font
        disp = display(n)
        pad = [v * self.k for v in side(n, "padding", f["size"])]
        bg = css_lite.color(n.style.get("background-color") or n.style.get("background"))
        start = len(self.items)
        bt, bb = border(n, "top"), border(n, "bottom")
        bl = border(n, "left")
        ex_w = css_lite.length_pt(n.style.get("width"), f["size"], container=w)
        if ex_w and ex_w < w and n.tag not in ("table",):
            w = ex_w
        ix, iy, iw = x + pad[3] + (bl["w"] + 3 if bl else 0), y + pad[0], w - pad[1] - pad[3] - (bl["w"] + 3 if bl else 0)
        if n.tag == "table":
            h = self.table(n, x, y, w)
            return h
        if n.tag in ("ul", "ol"):
            h = self.list_(n, ix, iy, iw)
        elif n.tag == "svg":
            self.dropped += 1
            labels = svg_text(n)
            h = self.text_box([[run_of("（図）" + "　".join(labels), dict(f, size=f["size"] * 0.9))]], ix, iy, iw, f) if labels else 0
        elif n.tag == "img":
            h = self.image(n, ix, iy, iw)
        elif (disp.endswith("grid") or (disp.endswith("flex") and "column" not in n.style.get("flex-direction", ""))) \
                and len([c for c in n.elements() if not hidden(c)]) >= 2:
            h = self.columns(n, ix, iy, iw, disp)
        else:
            h = self.flow(n, ix, iy, iw, disp, role_title)
        h_ex = css_lite.length_pt(n.style.get("height"), f["size"])
        if h_ex and h == 0 and bg:  # 文字の無い飾りの棒（表紙の線など）
            h = h_ex * self.k
        if h == 0 and not bg:
            return 0.0
        total = h + pad[0] + pad[2]
        if bg and bg.lower() not in ("#ffffff",) and total > 0:
            self.items.insert(start, {"t": "rect", "x": x, "y": y, "w": w, "h": total, "fill": bg})
        if bt:
            self.items.append({"t": "line", "x1": x, "y1": y, "x2": x + w, "y2": y, "color": bt["color"], "w": bt["w"]})
        if bb:
            self.items.append({"t": "line", "x1": x, "y1": y + total + 2, "x2": x + w, "y2": y + total + 2,
                               "color": bb["color"], "w": bb["w"]})
            total += 4
        if bl:
            self.items.append({"t": "line", "x1": x + bl["w"] / 2, "y1": y, "x2": x + bl["w"] / 2, "y2": y + total,
                               "color": bl["color"], "w": bl["w"]})
        return total

    def gap(self, n, prev, disp):
        g = css_lite.length_pt((n.style.get("row-gap") or n.style.get("gap") or "").split()[0] if
                               (n.style.get("row-gap") or n.style.get("gap")) else None, n.font["size"])
        if g is not None and (disp.endswith("flex") or disp.endswith("grid")):
            return g * self.k
        mb = side(prev, "margin", prev.font["size"])[2] if prev is not None else 0
        return max(mb, 0) * self.k

    def flow(self, n, x, y, w, disp, role_title=None):
        h, runs, prev = 0.0, [], None
        title_role = "title" if role_title is not None and role_title is n else None

        def flush():
            nonlocal h, runs
            paras = split_paras(runs)
            if paras:
                h += self.text_box(paras, x, y + h, w, n.font, role=title_role)
            runs = []
        for c in n.children:
            if isinstance(c, Node) and not hidden(c) and is_block(c, disp):
                flush()
                mt = max(0.0, side(c, "margin", c.font["size"])[0]) * self.k if c.style.get("margin") or c.style.get("margin-top") else 0
                g = self.gap(n, prev, disp) if prev is not None else 0
                if c.tag == "p" and not (c.style.get("margin") or c.style.get("margin-top")):
                    mt = c.font["size"] * 0.5 * self.k if prev is not None else 0
                dh = self.block(c, x, y + h + max(g, mt), w, disp, role_title)
                if dh:
                    h += max(g, mt) + dh
                    prev = c
            elif isinstance(c, Node) and c.tag == "br":
                runs.append({"text": "\n"})
            elif isinstance(c, Node):
                if not hidden(c):
                    inline_runs(c, runs)
            else:
                t = re.sub(r"[ \t\r\f]*\n[ \t\r\f\n]*", NL, c)
                t = re.sub(r"[ \t\r\f]+", " ", t).replace(" ", " ")
                if t:
                    runs.append(run_of(t, n.font))
        flush()
        return h

    def list_(self, n, x, y, w):
        h = 0.0
        for i, li in enumerate([c for c in n.elements() if c.tag == "li" and not hidden(c)]):
            runs, subs = [], []
            for c in li.children:
                if isinstance(c, Node) and c.tag in ("ul", "ol"):
                    subs.append(c)
                elif isinstance(c, Node):
                    if not hidden(c):
                        if is_block(c):
                            runs.append({"text": "\n"})
                        inline_runs(c, runs)
                else:
                    runs.append(run_of(re.sub(r"\s+", " ", c), li.font))
            paras = split_paras(runs)
            if i:
                h += max(2.0, side(li, "margin", li.font["size"])[2]) * self.k
            char = f"{i + 1}." if n.tag == "ol" else "•"
            if paras:
                if n.tag == "ol":
                    paras[0] = [run_of(char + " ", li.font)] + paras[0]
                    h += self.text_box(paras, x, y + h, w, li.font)
                else:
                    h += self.text_box(paras, x, y + h, w, li.font, bullet="•")
            for s in subs:
                h += self.list_(s, x + li.font["size"] * self.k * 1.2, y + h, w - li.font["size"] * self.k * 1.2)
        return h

    def image(self, n, x, y, w):
        src = n.attrs.get("src", "")
        p = (self.base_dir / src) if src and not re.match(r"^(https?:|data:)", src) else None
        if p is None or not p.exists():
            self.dropped += 1
            return 0.0
        try:
            from pptx.parts.image import Image
            px_w, px_h = Image.from_file(str(p)).size
        except Exception:  # 読めない画像は貼らない（数えて build.py が知らせる）
            self.dropped += 1
            return 0.0
        ww = min(w, css_lite.length_pt(n.style.get("width") or n.attrs.get("width"), 12, container=w) or w)
        hh = ww * px_h / max(1, px_w)
        if hh > 300 * self.k:
            hh = 300 * self.k
            ww = hh * px_w / max(1, px_h)
        self.items.append({"t": "img", "file": str(p.resolve()), "x": x, "y": y, "w": ww, "h": hh})
        return hh

    def columns(self, n, x, y, w, disp):
        kids = [c for c in n.elements() if not hidden(c)]
        gap_v = (n.style.get("column-gap") or n.style.get("gap") or "").split()
        gap = (css_lite.length_pt(gap_v[-1], n.font["size"]) if gap_v else None)
        gap = (gap if gap is not None else 12.0) * self.k
        tmpl = []
        if disp.endswith("grid"):
            spec = n.style.get("grid-template-columns", "")
            spec = re.sub(r"minmax\([^()]*\)", "1fr", spec)
            spec = re.sub(r"repeat\(\s*(auto-fit|auto-fill)\s*,\s*([^)]+)\)",
                          lambda m: " ".join([m.group(2).strip()] * max(1, len(kids))), spec)
            spec = re.sub(r"repeat\(\s*(\d+)\s*,\s*([^)]+)\)", lambda m: " ".join([m.group(2).strip()] * int(m.group(1))), spec)
            tmpl = spec.split()
        ncol = len(tmpl) if tmpl else (len(kids) if disp.endswith("flex") else 1)
        if ncol <= 1:
            return self.flow(n, x, y, w, "block")
        h, rowgap = 0.0, (css_lite.length_pt((n.style.get("row-gap") or n.style.get("gap") or "0").split()[0], n.font["size"]) or 0) * self.k
        spans = [_col_span(c, ncol) for c in kids]
        if tmpl and any(sp > 1 for sp in spans):
            # grid-column: span N / a / b がある格子: 列の幅は型だけから決め、子は前から順に N 列ずつ使う
            ws = self._col_widths([None] * ncol, tmpl, w - gap * (ncol - 1), disp)
            col, cx, rh, first = 0, x, 0.0, True
            for c, sp in zip(kids, spans):
                sp = min(sp, ncol)
                if col + sp > ncol:
                    h += rh + rowgap
                    col, cx, rh = 0, x, 0.0
                cw = sum(ws[col:col + sp]) + gap * (sp - 1)
                rh = max(rh, self.block(c, cx, y + h, cw, disp))
                cx += cw + gap
                col += sp
            return h + rh
        for r0 in range(0, len(kids), ncol):
            row = kids[r0:r0 + ncol]
            ws = self._col_widths(row, tmpl, w - gap * (ncol - 1), disp)
            cx, rh = x, 0.0
            for c, cw in zip(row, ws):
                rh = max(rh, self.block(c, cx, y + h, cw, disp))
                cx += cw + gap
            h += rh + (rowgap if r0 + ncol < len(kids) else 0)
        return h

    def _col_widths(self, row, tmpl, avail, disp):
        fixed, weights = [], []
        for i in range(max(len(row), len(tmpl))):
            t = tmpl[i] if i < len(tmpl) else "1fr"
            c = row[i] if i < len(row) else None
            empty = c is not None and not _has_text(c)
            if t.endswith("fr"):
                fixed.append(None)
                weights.append(float(t[:-2] or 1))
            elif t == "auto" or (disp.endswith("flex") and not tmpl):
                if empty:
                    fixed.append(18.0 * self.k)
                    weights.append(0)
                else:
                    g = c.style.get("flex", "") if c is not None else ""
                    fixed.append(None)
                    weights.append(float(g.split()[0]) if g and re.match(r"^[\d.]+$", g.split()[0]) else 1.0)
            else:
                v = css_lite.length_pt(t, 12)
                fixed.append(v * self.k if v else None)
                weights.append(0 if v else 1)
        rest = max(20.0, avail - sum(v for v in fixed if v))
        tw = sum(wt for wt, fx in zip(weights, fixed) if fx is None) or 1
        out = [fx if fx is not None else rest * wt / tw for fx, wt in zip(fixed, weights)]
        return out[:len(row)]

    # --- 表
    def table(self, n, x, y, w):
        rows = []

        def collect(e):
            for c in e.elements():
                if c.tag == "tr" and not hidden(c):
                    rows.append([d for d in c.elements() if d.tag in ("td", "th") and not hidden(d)])
                elif c.tag in ("thead", "tbody", "tfoot"):
                    collect(c)
        collect(n)
        rows = [r for r in rows if r]
        if not rows:
            return 0.0
        # 結合を含めた格子
        grid, cells = {}, []
        for ri, r in enumerate(rows):
            ci = 0
            for d in r:
                while (ri, ci) in grid:
                    ci += 1
                cs = max(1, int(d.attrs.get("colspan", "1") or 1))
                rs = max(1, int(d.attrs.get("rowspan", "1") or 1))
                for a in range(rs):
                    for b in range(cs):
                        grid[(ri + a, ci + b)] = d
                cells.append((ri, ci, rs, cs, d))
                ci += cs
        nr = max(r for r, _ in grid) + 1
        nc = max(c for _, c in grid) + 1
        # 列の幅: 幅の指定（style の width）を優先、残りは中身の長さで分ける
        fixed, weight = [None] * nc, [3.0] * nc
        for ri, ci, rs, cs, d in cells:
            if cs == 1:
                v = css_lite.length_pt(d.style.get("width"), d.font["size"])
                if v and fixed[ci] is None:
                    fixed[ci] = v
                weight[ci] = max(weight[ci], min(28.0, text_em(_plain(d)) * d.font["size"] / 12))
        rest = max(40.0, w - sum(v for v in fixed if v))
        tw = sum(wt for wt, fx in zip(weight, fixed) if fx is None) or 1
        cols = [fx if fx is not None else rest * wt / tw for fx, wt in zip(fixed, weight)]
        scale = w / sum(cols)
        cols = [c * scale for c in cols]
        heights = [0.0] * nr
        out_cells, tall = [], []
        for ri, ci, rs, cs, d in cells:
            f = d.font
            pad = [v * self.k for v in side(d, "padding", f["size"])] if (d.style.get("padding") or any(
                d.style.get(f"padding-{s}") for s in ("top", "right", "bottom", "left"))) else [4.0, 5.0, 4.0, 5.0]
            cw = sum(cols[ci:ci + cs]) - pad[1] - pad[3]
            runs = []
            paras = []
            for c in d.children:
                if isinstance(c, Node) and c.tag in ("ul", "ol") and not hidden(c):
                    if runs:
                        paras += [{"runs": p} for p in split_paras(runs)]
                        runs = []
                    for li in [x for x in c.elements() if x.tag == "li" and not hidden(x)]:
                        for p in split_paras(inline_runs(li, [])):
                            paras.append({"runs": p, "bullet": True})
                elif isinstance(c, Node):
                    if not hidden(c):
                        if is_block(c) and runs:
                            runs.append({"text": "\n"})
                        inline_runs(c, runs)
                else:
                    t = re.sub(r"[ \t\r\f]*\n[ \t\r\f\n]*", NL, c)
                    runs.append(run_of(re.sub(r"[ \t\r\f]+", " ", t), f))
            paras += [{"runs": p} for p in split_paras(runs)]
            need, out_p = pad[0] + pad[2], []
            for p in paras:
                rr = [dict(r, size=r["size"] * self.k) for r in p["runs"]]
                size = max(r["size"] for r in rr)
                lh = size * max(1.0, f["lh"])
                hang = size if p.get("bullet") else 0
                need += wrap_lines("".join(r["text"] for r in rr), size, cw - hang) * lh
                q = {"runs": rr, "align": f["align"], "lineHeight": lh}
                if p.get("bullet"):
                    q["bullet"] = {"char": "•", "color": rr[0]["color"], "size": size}
                    q["hang"] = hang
                out_p.append(q)
            if rs == 1:
                heights[ri] = max(heights[ri], need)
            else:
                tall.append((ri, rs, need))
            va = d.style.get("vertical-align", "middle").strip()
            out_cells.append({"r": ri, "c": ci, "rs": rs, "cs": cs, "pad": pad, "paras": out_p,
                              "valign": {"top": "top", "bottom": "bottom"}.get(va, "middle"),
                              "fill": css_lite.color(d.style.get("background-color") or d.style.get("background")),
                              "borders": [border(d, s) for s in ("top", "right", "bottom", "left")]})
        heights = [max(h, 12.0 * self.k) for h in heights]
        for ri, rs, need in tall:  # 縦に結合したセル: 最後の行だけで中身が入る高さにする（pptx_metrics.table_row_heights と同じ理由）
            last = min(nr, ri + rs) - 1
            heights[last] = max(heights[last], need)
        self.items.append({"t": "table", "x": x, "y": y, "w": w, "h": sum(heights), "rows": heights, "cols": cols,
                           "cells": out_cells})
        return sum(heights)


def _col_span(n, ncol):
    """grid-column の指定 → 使う列の数（span N・a / b・a / -1）。無ければ 1。"""
    v = (n.style.get("grid-column") or "").replace(" ", "")
    m = re.match(r"^(?:\d+/)?span(\d+)$", v)
    if m:
        return int(m.group(1))
    m = re.match(r"^(-?\d+)/(-?\d+)$", v)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if b < 0:
            b = ncol + 2 + b
        return max(1, b - a)
    return 1


def _plain(n):
    return re.sub(r"\s+", "", "".join(c if isinstance(c, str) else _plain(c) for c in n.children if isinstance(c, str) or not hidden(c)))


def _has_text(n):
    if hidden(n):
        return False
    if n.tag == "svg":
        return bool(svg_text(n))
    return any((isinstance(c, str) and c.strip()) or (isinstance(c, Node) and _has_text(c)) for c in n.children)


# ---------------------------------------------------------------- スライド
def _sides(c, W, H):
    """position:absolute の子の top / right / bottom / left（pt、無い辺は None）。inset も読む。"""
    out = dict.fromkeys(("top", "right", "bottom", "left"))
    ins = (c.style.get("inset") or "").split()
    if ins:
        vals = ins + ins[:1] * (4 - len(ins)) if len(ins) == 1 else (ins * 2 if len(ins) == 2 else (ins + [ins[1]] if len(ins) == 3 else ins))
        for k, v, box in zip(("top", "right", "bottom", "left"), vals[:4], (H, W, H, W)):
            out[k] = css_lite.length_pt(v, 12, container=box)
    for k, box in (("top", H), ("right", W), ("bottom", H), ("left", W)):
        v = css_lite.length_pt(c.style.get(k), 12, container=box)
        if v is not None:
            out[k] = v
    return out


def _slide_box(sec):
    """スライドの要素の大きさ（CSS の単位のまま、pt）。読めなければ 960×540。"""
    W = css_lite.length_pt(sec.style.get("width"), 12)
    H = css_lite.length_pt(sec.style.get("height"), 12)
    if not W or W < 100:
        W = SLIDE_W
    if not H or H < 50:
        H = W * 9 / 16
    return W, H


def layout_slide(sec, base_dir):
    """1 枚 → {"bg", "items"}。スライドの CSS の単位のまま組み、最後に 960pt 幅にそろえる。はみ出す時は字を小さくして組み直す。"""
    bg = css_lite.color(sec.style.get("background-color") or sec.style.get("background")) or "#ffffff"
    W, H = _slide_box(sec)
    pad = side(sec, "padding", sec.font["size"])
    if not any(pad):
        pad = [W * 0.05, W * 0.047, H * 0.04, W * 0.047]
    pad[1] = pad[1] or W * 0.047
    pad[3] = pad[3] or W * 0.047
    x, w = pad[3], W - pad[1] - pad[3]
    kids = [c for c in sec.elements() if not hidden(c)]
    flow_kids = [c for c in kids if c.style.get("position") != "absolute"]
    abs_kids = [c for c in kids if c.style.get("position") == "absolute"]
    # 上下とも位置を決めた子（.sinner{position:absolute; inset:…} など）は、スライドの本体として流して組む
    regions = []
    for c in list(abs_kids):
        sd = _sides(c, W, H)
        if sd["top"] is not None and sd["bottom"] is not None:
            left = sd["left"] if sd["left"] is not None else x
            right = sd["right"] if sd["right"] is not None else W - x - w
            regions.append((c, left, sd["top"], W - left - right, H - sd["bottom"]))
            abs_kids.remove(c)
    title = _find_title(sec)
    k = 1.0
    while True:
        lay = Layout(base_dir, k)
        limit = H - max(pad[2], 8.0)
        for c in abs_kids:  # 下か上に寄せる部品（フッターなど）
            sd = _sides(c, W, H)
            cx = sd["left"] if sd["left"] is not None else x
            cw = W - cx - (sd["right"] if sd["right"] is not None else W - x - w)
            probe = Layout(base_dir, 1.0)
            ch = probe.block(c, cx, 0, cw)
            lay.dropped += probe.dropped
            if sd["bottom"] is not None:
                cy = H - sd["bottom"] - ch
                limit = min(limit, cy - 4)
            else:
                cy = sd["top"] or 0
            for it in probe.items:
                _shift(it, cy)
            lay.items += probe.items
        over = 0.0
        y = pad[0]
        prev = None
        for c in flow_kids:
            mt = max(0.0, side(c, "margin", c.font["size"])[0]) * k
            mb = max(0.0, side(prev, "margin", prev.font["size"])[2]) * k if prev is not None else 0
            dh = lay.block(c, x, y + max(mt, mb), w, "", title)
            if dh:
                y += max(mt, mb) + dh
                prev = c
        over = max(over, y - limit)
        for c, rx, ry, rw, rbottom in regions:
            rows = (c.style.get("grid-template-rows") or "").split()
            ch = [e for e in c.elements() if not hidden(e)]
            if display(c).endswith("grid") and len(rows) == len(ch) >= 2 and rows[-1] == "auto" and "1fr" in rows[:-1]:
                # 「… 1fr auto」の格子: 最後の行（フッター）は下に付ける
                yy = ry
                for e in ch[:-1]:
                    yy += lay.block(e, rx, yy, rw, "", title)
                probe = Layout(base_dir, k)
                fh = probe.block(ch[-1], rx, 0, rw)
                lay.dropped += probe.dropped
                fy = max(yy + 4, min(rbottom, limit) - fh)
                for it in probe.items:
                    _shift(it, fy)
                lay.items += probe.items
                over = max(over, fy + fh - min(rbottom, limit))
                continue
            dh = lay.block(c, rx, ry, rw, "", title)
            over = max(over, ry + dh - min(rbottom, limit))
        if over <= 0 or k <= MIN_SCALE:
            f = SLIDE_W / W
            return {"bg": bg, "items": [_scale(it, f) for it in lay.items], "scale": k, "overflow": max(0.0, over) * f,
                    "dropped": lay.dropped}
        k = max(MIN_SCALE, k * 0.92)


def _scale(it, f):
    """CSS の単位で組んだ記録を 960pt 幅にそろえる。"""
    if f == 1:
        return it
    it = dict(it)
    for key in ("x", "y", "w", "h", "x1", "y1", "x2", "y2"):  # 線の "w" は線の太さ（これも同じ割合）
        if key in it:
            it[key] = it[key] * f

    def paras(ps):
        out = []
        for p in ps:
            q = dict(p, runs=[dict(r, size=r["size"] * f) for r in p["runs"]], lineHeight=p["lineHeight"] * f)
            if q.get("hang"):
                q["hang"] = q["hang"] * f
            if q.get("bullet"):
                q["bullet"] = dict(q["bullet"], size=q["bullet"]["size"] * f)
            out.append(q)
        return out
    if it.get("t") == "text":
        it["paras"] = paras(it["paras"])
    if it.get("t") == "table":
        it["rows"] = [r * f for r in it["rows"]]
        it["cols"] = [c * f for c in it["cols"]]
        it["cells"] = [dict(c, pad=[v * f for v in c["pad"]], paras=paras(c["paras"]),
                            borders=[dict(b, w=b["w"] * f) if b else None for b in c["borders"]]) for c in it["cells"]]
    return it


def _find_title(sec):
    def walk(n):
        for c in n.elements():
            if hidden(c):
                continue
            if c.tag == "h1" or (TITLE_CLASSES & c.classes):
                return c
            r = walk(c)
            if r is not None:
                return r
        return None
    return walk(sec)


def _shift(it, dy):
    if "y" in it:
        it["y"] += dy
    if "y1" in it:
        it["y1"] += dy
        it["y2"] += dy


def dump(html_path):
    """HTML → html_dump.mjs と同じ形の描画の記録（slideW = 960、単位 pt）。"""
    html = Path(html_path).read_text(encoding="utf-8", errors="replace")
    t = _Tree()
    t.feed(html)
    t.close()
    _mark_siblings(t.root)
    styler = Styler(html)
    styler.apply(t.root)
    slides = find_slides(t.root, [])
    base = Path(html_path).resolve().parent
    out = [layout_slide(s, base) for s in slides]
    return {"slideW": SLIDE_W, "slides": out}


def convert(html, out, notes=None, author="", title=None):
    """build.py の予備の書き出し。戻り値 (スライド数, ノートの枚数, はみ出しを字の縮小で直せなかった枚の番号,
    {枚の番号: 入れられなかった画像・図の数})。"""
    from html_to_pptx import assemble
    deck = parse_deck(Path(html))
    if notes is None:
        notes = [s.notes for s in deck.slides]
    data = dump(html)
    n, n_notes = assemble(data, deck, notes, out, author, title)
    over = [i for i, s in enumerate(data["slides"], 1) if s["overflow"] > 2]
    dropped = {i: s["dropped"] for i, s in enumerate(data["slides"], 1) if s.get("dropped")}
    return n, n_notes, over, dropped


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    html = args[0]
    out = args[1] if len(args) > 1 else str(Path(html).with_suffix(".pptx"))
    n, n_notes, over, dropped = convert(html, out)
    print(f"{n} slides（ノート {n_notes} 枚・Chrome を使わない予備の書き出し） → {out}")
    if over:
        print(f"注意: {', '.join(f'p{i}' for i in over)} は字を小さくしても枠に収まりきらない")
    if dropped:
        print("注意: 画像・図を入れられなかった枚: " + "・".join(f"p{i}（{k} 個）" for i, k in dropped.items()))


if __name__ == "__main__":
    main()
