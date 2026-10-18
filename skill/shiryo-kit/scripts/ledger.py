"""shiryo-kit: 出典台帳（ledger.md の Markdown 表）を読み、スライド本文・読み原稿の語と突き合わせる。

check.py ledger が使う。台帳の形式は references/html-contract.md「出典台帳の形式」が正本。要点:
  - 列: ID | 主張 | 表記 | 区分 | 出典URL | 取得日 | 引用 | 適用時点 | 使用箇所 | 備考（表記・使用箇所・備考は省略可）
  - 区分: 確認済み / 未確認 / 本人提供
  - 確認済み: 出典URL（http/https）・取得日（日付）・引用（原典の文そのまま）・適用時点 が必須。
    主張に書いた数字・金額・率・日付は、引用か適用時点に同じ値が無ければ食い違いとして FAIL（漢数字は数字に直して比べる）
  - スライドと読み原稿の数字・日付・率・金額・法令名・条番号は、どれかの行の 主張 か 表記 に同じ値で載っていること
  - 未確認の行にだけ当たる語は、同じ文章塊（スライド）・同じ行（読み原稿・配布資料）に [要確認] を出すこと
  - 照合する file: HTML デッキ（本文とノート）・読み原稿 .md・配布資料 .md/.txt/.docx など、渡したもの全部
"""
import re
from dataclasses import dataclass, field

from claims import extract, kanji_numerals_to_digits

STATUS = {"確認済み": "確認済み", "確認済": "確認済み", "原典確認済み": "確認済み", "原典確認済": "確認済み",
          "未確認": "未確認", "要確認": "未確認", "本人提供": "本人提供", "本人": "本人提供", "提供": "本人提供"}
COLS = {
    "id": ("ID", "id", "番号", "No", "No."),
    "claim": ("主張", "内容", "主張・数字"),
    "forms": ("表記", "資料での表記", "表記ゆれ"),
    "status": ("区分", "状態", "ステータス"),
    "url": ("出典URL", "出典 URL", "URL", "出典"),
    "date": ("取得日", "確認日", "取得・確認日"),
    "quote": ("引用", "原文", "該当箇所", "引用（原文）"),
    "applies": ("適用時点", "時点", "施行日・適用時点", "適用"),
    "where": ("使用箇所", "場所", "ページ", "使用場所"),
    "memo": ("備考", "メモ"),
}
EMPTY = {"", "-", "—", "ー", "なし", "無し", "未", "n/a", "N/A", "TBD", "未取得"}
MARK = re.compile(r"[\[［【]\s*要確認\s*[\]］】]")
DATE_RX = re.compile(r"\d{4}\s*[-/年.]\s*\d{1,2}(?:\s*[-/月.]\s*\d{1,2})?|(?:令和|平成)\s*\d+\s*年")


@dataclass
class Row:
    line: int
    cells: dict
    tokens: list = field(default_factory=list)
    pages: set = field(default_factory=set)
    notes_ok: bool = True

    def get(self, k):
        return (self.cells.get(k) or "").strip()

    @property
    def status(self):
        return STATUS.get(re.sub(r"\s", "", self.get("status")), None)

    @property
    def rid(self):
        return self.get("id") or f"{self.line}行目"


def _split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells = re.split(r"(?<!\\)\|", s)
    return [c.replace("\\|", "|").replace("<br>", "\n").replace("<br/>", "\n").strip() for c in cells]


def _col_key(name):
    n = re.sub(r"\s", "", name)
    for k, aliases in COLS.items():
        if n in {re.sub(r"\s", "", a) for a in aliases}:
            return k
    return None


def parse_ledger(text):
    """(rows, errors)。errors は台帳そのものの不備（列が無い等）。"""
    rows, errors = [], []
    lines = text.splitlines()
    i = 0
    found_table = False
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.strip().startswith("|") and re.match(r"^\s*\|?\s*:?-{3,}", nxt):
            header = [_col_key(c) for c in _split_row(line)]
            if "status" in header and "claim" in header:
                found_table = True
                i += 2
                while i < len(lines) and lines[i].strip().startswith("|"):
                    vals = _split_row(lines[i])
                    cells = {k: v for k, v in zip(header, vals) if k}
                    if any(v.strip() for v in cells.values()):
                        rows.append(Row(i + 1, cells))
                    i += 1
                continue
        i += 1
    if not found_table:
        errors.append("台帳に表が見つからない（見出し行に「主張」と「区分」の列が要る — references/html-contract.md「出典台帳の形式」）")
    for r in rows:
        r.tokens = extract(r.get("claim") + "\n" + r.get("forms"))
        r.pages = parse_pages(r.get("where"))
    return rows, errors


def parse_pages(s):
    pages = set()
    s = s.replace("〜", "-").replace("～", "-").replace("–", "-")
    for a, b in re.findall(r"(?:p|P|P\.|p\.|スライド|ｐ)\s*(\d+)(?:\s*-\s*(?:p|P|P\.|p\.)?\s*(\d+))?", s):
        lo, hi = int(a), int(b or a)
        pages.update(range(lo, hi + 1))
    for a in re.findall(r"(\d+)\s*枚目", s):
        pages.add(int(a))
    return pages


def validate_rows(rows):
    out = []
    seen = {}
    for r in rows:
        if r.get("id"):
            if r.get("id") in seen:
                out.append(f"台帳 {r.rid}: ID が重複（{seen[r.get('id')]}行目と{r.line}行目）")
            seen.setdefault(r.get("id"), r.line)
        st = r.status
        if st is None:
            out.append(f"台帳 {r.rid}: 区分「{r.get('status')}」が不明（確認済み / 未確認 / 本人提供 のどれか）")
            continue
        if not r.get("claim"):
            out.append(f"台帳 {r.rid}: 主張が空")
        if st != "確認済み":
            continue
        if not re.search(r"https?://\S+", r.get("url")):
            out.append(f"台帳 {r.rid}: 確認済みなのに出典URLが無い（取れなかったなら区分を 未確認 にする）")
        if r.get("date") in EMPTY or not DATE_RX.search(r.get("date")):
            out.append(f"台帳 {r.rid}: 確認済みなのに取得日が無い（例: 2026-10-18）")
        if r.get("quote") in EMPTY:
            out.append(f"台帳 {r.rid}: 確認済みなのに引用（原典の該当箇所の文）が無い（モデルの記憶だけで確認済みにしない）")
        if r.get("applies") in EMPTY:
            out.append(f"台帳 {r.rid}: 確認済みなのに適用時点（施行日・経過措置・対象）が無い")
        if r.get("quote") not in EMPTY:
            src = kanji_numerals_to_digits(r.get("quote") + "\n" + r.get("applies"))
            src_tokens = extract(src)
            claim_tokens = [t for t in extract(r.get("claim")) if t.kind not in ("law", "art")]
            for t in claim_tokens:
                if not any(t.matches(s) for s in src_tokens):
                    out.append(f"台帳 {r.rid}: 主張の「{t.raw}」が引用・適用時点に見当たらない（原典と食い違う数字か、引用が足りない）")
    return out


def _candidates(tok, rows, page):
    cands = [r for r in rows if r.status and any(tok.matches(t) for t in r.tokens)]
    if tok.kind == "law" and not cands:
        cands = [r for r in rows if r.status and tok.key[0] in re.sub(r"\s", "", r.get("claim") + r.get("forms"))]
    narrowed = [r for r in cands if page is not None and page in r.pages]
    return narrowed or cands


def deck_units(deck, label=""):
    """スライドの文章塊・読み原稿の行を照合の単位にする: (ページ, 場所, 照合する文字, [要確認] を探す文字)。"""
    pre = f"{label} " if label else ""
    units = []
    for s in deck.slides:
        units += [(s.index, f"{pre}p{s.index} 本文", b.ledger_text, b.text) for b in s.blocks]
        units += [(s.index, f"{pre}p{s.index} 読み原稿", line, line) for line in s.notes.split("\n") if line.strip()]
    return units


def text_units(text, label):
    """Markdown・テキスト・docx から取り出した文字: 1 行（段落）を 1 単位にする。ページは無い。"""
    units = []
    in_comment = False
    for i, line in enumerate(text.splitlines(), 1):
        # HTML コメントの中と「<!-- ledger:skip -->」を付けた行は照合しない（読み原稿 md の字数の行など）
        if "<!-- ledger:skip -->" in line:
            continue
        if in_comment or line.strip().startswith("<!--"):
            in_comment = "-->" not in line
            continue
        if line.strip():
            units.append((None, f"{label}:{i}", line, line))
    return units


def check_units(units, rows):
    """語が台帳に載っているか・未確認の行にだけ当たる語に [要確認] があるかを見る。"""
    out = []
    seen = set()
    for page, where, ltext, full in units:
        for tok in extract(ltext):
            key = (where, tok.raw)
            if key in seen:
                continue
            cands = _candidates(tok, rows, page)
            if not cands:
                seen.add(key)
                out.append(f"{where}: 「{tok.raw}」が出典台帳に無い（行を足す。本人の情報なら区分=本人提供）"
                           f" — 「{_snip(full, tok.raw)}」")
                continue
            if all(r.status == "未確認" for r in cands) and not MARK.search(full):
                seen.add(key)
                ids = ",".join(r.rid for r in cands[:3])
                out.append(f"{where}: 「{tok.raw}」は未確認（台帳 {ids}）なのに [要確認] が無い — 「{_snip(full, tok.raw)}」")
    return out


def check_deck_against(deck, rows):
    return check_units(deck_units(deck), rows)


def _snip(text, raw, width=24):
    t = text.replace("\n", " ")
    i = t.find(raw)
    if i < 0:
        return t[:width * 2]
    a = max(0, i - width)
    return ("…" if a else "") + t[a:i + len(raw) + width] + ("…" if i + len(raw) + width < len(t) else "")
