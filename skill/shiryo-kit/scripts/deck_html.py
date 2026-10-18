"""shiryo-kit: HTML デッキを標準ライブラリだけで読み、スライドごとの タイトル・文章塊・読み原稿（ノート）を取り出す。

check.py（deck / ledger / pptx）・build.py（読み原稿 md・pptx のノート）が共通で使う。Chrome は使わない（静的な読み取り）。
スライドの見つけ方は html_dump.mjs と同じ: section.s / section.slide / .slide のうち、別のスライドの内側に無いもの。
ノートの契約（references/html-contract.md）:
  - スライド要素の内側の <aside class="notes"> … </aside>（複数可。<p>・<br>・<li> で段落を分ける）
  - または スライド要素の data-notes="…" 属性（両方あれば data-notes → aside の順につなぐ）
"""
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {"address", "article", "aside", "blockquote", "caption", "dd", "div", "dl", "dt", "figcaption", "figure",
         "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "li", "main", "nav", "ol", "p", "pre", "section",
         "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul"}
SKIP_TAGS = {"script", "style", "template", "noscript", "head", "title"}
MEDIA = {"img", "svg", "canvas", "video", "picture", "iframe"}
AUTO_CLOSE = {"p", "li", "dt", "dd", "tr", "td", "th", "option"}
# 出典台帳の照合から外す部品（ページ番号・見出しバー・目次の番号・出典行など）。data-ledger="skip" でも外せる
LEDGER_SKIP_CLASSES = {"foot", "bar", "logo", "date", "tn", "tp", "ref", "no", "cn", "cno", "src", "pageno"}
TITLE_CLASSES = {"ttl", "title", "msg"}
CJK = "　-鿿＀-￯"
NL = "\u0001"


def _collapse(s):
    return re.sub(r"[ \t\n\r\f]+", lambda m: NL if re.search(r"[\n\r]", m.group(0)) else " ", s).replace(" ", " ")


def _lines(s):
    return "\n".join(x for x in (finish_text(y) for y in s.split("\n")) if x)


def finish_text(s):
    """html_dump.mjs と同じ空白規則: 和文同士の間のソース改行由来の空白だけ詰め、作者の空白・全角空白は残す。"""
    s = re.sub(rf"(?<=[{CJK}])[{NL}]+(?=[{CJK}])", "", s)
    s = re.sub(rf"[ {NL}]+", " ", s)
    return s.strip(" ")


@dataclass
class Block:
    text: str            # 描画される文字（静的な読み取り）
    ledger_text: str     # 出典台帳の照合に使う文字（ページ番号・出典行など LEDGER_SKIP の部分を除く）
    tag: str
    is_title: bool = False
    order: int = 0


@dataclass
class Slide:
    index: int
    classes: list
    title: str = ""
    blocks: list = field(default_factory=list)
    notes: str = ""
    has_table: int = 0
    has_media: int = 0

    @property
    def text(self):
        return "\n".join(b.text for b in self.blocks)

    @property
    def label(self):
        """見出しの代わりに使う名前（タイトルが無い表紙・裏表紙は最初の本文の塊）。"""
        if self.title:
            return self.title
        for b in self.blocks:
            if b.ledger_text.strip():
                return b.ledger_text.split("\n")[0]
        return ""

    @property
    def is_cover(self):
        return bool({"cover", "chap"} & set(self.classes))


@dataclass
class Deck:
    title: str
    slides: list


class _El:
    __slots__ = ("tag", "attrs", "classes", "buf", "skip_ledger", "hidden", "order", "slide", "notes", "is_title")

    def __init__(self, tag, attrs, order):
        self.tag = tag
        self.attrs = attrs
        self.classes = (attrs.get("class") or "").split()
        self.buf = []
        self.skip_ledger = False
        self.hidden = False
        self.order = order
        self.slide = None
        self.notes = False
        self.is_title = False


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.slides = []
        self.cur = None  # 今のスライド
        self.order = 0
        self.doc_title = []
        self.in_title = False
        self.skip_depth = 0
        self.notes_buf = None

    # --- helpers
    def _is_slide(self, el):
        c = set(el.classes)
        return (el.tag == "section" and ("s" in c or "slide" in c)) or "slide" in c

    def _nearest_block(self):
        for el in reversed(self.stack):
            if el.tag in BLOCK or el.slide is not None:
                return el
        return None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "title" and not self.stack_has("body"):
            self.in_title = True
        if tag in SKIP_TAGS or self.skip_depth:
            if tag not in VOID:
                self.skip_depth += 1
            return
        if tag in AUTO_CLOSE and self.stack and self.stack[-1].tag == tag:
            self._close(self.stack[-1])
        self.order += 1
        el = _El(tag, a, self.order)
        parent = self.stack[-1] if self.stack else None
        if parent is not None:
            el.skip_ledger = parent.skip_ledger
            el.hidden = parent.hidden
            el.notes = parent.notes
        style = a.get("style", "").replace(" ", "").lower()
        if "hidden" in a or "display:none" in style:
            el.hidden = True
        if a.get("data-ledger") == "skip" or (LEDGER_SKIP_CLASSES & set(el.classes)):
            el.skip_ledger = True
        if self.cur is None and self._is_slide(el):
            s = Slide(index=len(self.slides) + 1, classes=el.classes)
            if a.get("data-notes"):
                s.notes = a["data-notes"].strip()
            self.slides.append(s)
            self.cur = s
            el.slide = s
        elif self.cur is not None:
            if tag == "aside" and "notes" in el.classes and not el.notes:
                el.notes = True
                self.notes_buf = []
            if tag == "table" and not el.hidden and not el.notes:
                self.cur.has_table += 1
            if tag in MEDIA and not el.hidden and not el.notes:
                self.cur.has_media += 1
            if not self.cur.title and not el.notes and (tag == "h1" or (TITLE_CLASSES & set(el.classes))):
                el.is_title = True
        if tag == "br":
            self._data("\n")
            return
        if tag in VOID:
            return
        if el.notes and tag in BLOCK and self.notes_buf is not None:
            self.notes_buf.append("\n")
        self.stack.append(el)

    def stack_has(self, tag):
        return any(e.tag == tag for e in self.stack)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and not (tag in SKIP_TAGS or self.skip_depth):
            if self.stack and self.stack[-1].tag == tag:
                self._close(self.stack[-1])

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if self.skip_depth:
            if tag in SKIP_TAGS or tag not in VOID:
                self.skip_depth -= 1
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                while len(self.stack) > i:
                    self._close(self.stack[-1])
                return

    def _close(self, el):
        self.stack.pop()
        if el.notes and self.notes_buf is not None:
            parent_notes = self.stack and self.stack[-1].notes
            if el.tag in BLOCK:
                self.notes_buf.append("\n")
            if not parent_notes:  # aside.notes が閉じた
                txt = "\n".join(finish_text(x) for x in "".join(self.notes_buf).split("\n"))
                txt = re.sub(r"\n{2,}", "\n", txt).strip("\n")
                if txt and self.cur is not None:
                    self.cur.notes = (self.cur.notes + "\n" + txt).strip("\n") if self.cur.notes else txt
                self.notes_buf = None
            return
        if self.cur is None:
            return
        if el.tag in BLOCK or el.slide is not None:
            t = _lines("".join(c for c, _ in el.buf))
            if t and not el.hidden:
                lt = _lines("".join(c if not sk else "\n" for c, sk in el.buf))
                self.cur.blocks.append(Block(t, lt, el.tag, el.is_title, el.order))
                if el.is_title and not self.cur.title:
                    self.cur.title = t.replace("\n", " ")
        else:
            # インライン要素の文字は最寄りのブロックへ（タイトル判定はインライン要素にも付く: .ttl を span に付けた場合）
            if el.is_title and not self.cur.title and not el.hidden:
                t = _lines("".join(c for c, _ in el.buf)).replace("\n", " ")
                if t:
                    self.cur.title = t
            target = self._nearest_block()
            if target is not None:
                target.buf.extend(el.buf)
        if el.slide is not None:
            self.cur.blocks.sort(key=lambda b: b.order)
            self.cur = None

    def _data(self, data):
        if self.in_title:
            self.doc_title.append(data)
        if self.skip_depth or not self.stack:
            return
        top = self.stack[-1]
        if top.notes and self.notes_buf is not None:
            self.notes_buf.append(_collapse(data) if data != "\n" else "\n")
            return
        if self.cur is None:
            return
        if top.hidden:
            return
        top.buf.append((_collapse(data) if data != "\n" else "\n", top.skip_ledger))

    def handle_data(self, data):
        self._data(data)


def parse_deck(source):
    """source: パス or HTML 文字列。Deck を返す。"""
    if isinstance(source, Path) or (isinstance(source, str) and "<" not in source and Path(source).exists()):
        html = Path(source).read_text(encoding="utf-8", errors="replace")
    else:
        html = source
    p = _Parser()
    p.feed(html)
    p.close()
    while p.stack:
        p._close(p.stack[-1])
    title = finish_text(_collapse("".join(p.doc_title)))
    return Deck(title=title, slides=p.slides)


def strip_notes_markup(html):
    """<aside class="notes">…</aside> を取り除いた HTML（本文だけを検査する既存チェック用）。"""
    return re.sub(r"<aside\b[^>]*class=\"[^\"]*\bnotes\b[^\"]*\"[^>]*>.*?</aside>", "", html, flags=re.S | re.I)
