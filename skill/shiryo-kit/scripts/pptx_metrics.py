"""shiryo-kit: pptx の文字の大きさの推定（字数 × 字の大きさ ÷ 箱の幅）。check.py pptx・html_to_pptx.py・html_to_pptx_static.py が共通で使う。

PowerPoint・LibreOffice は Chrome より字の幅を広く取ることが多く、Chrome では 1 行に収まった表のセルが折り返して行が伸びる
（行の高さは「最小の高さ」なので、表全体が下に伸びて、下の出典の行などに重なる）。ここの推定は、その伸びを先に見積もるために
和文 1 字 = 1 em、英数字は広めに見る（控えめな側に倒した推定。実際より少し高く出ることはある）。
"""
import math
import unicodedata

EMU_PT = 12700


NO_LINE_START = set("、。，．,.)）」』】〕〉》｝]！？!?：；:;ー・々ぁぃぅぇぉっゃゅょァィゥェォッャュョ％%")


def char_w(ch):
    if ch in " \t":
        return 0.3
    ea = unicodedata.east_asian_width(ch)
    if ea in ("W", "F", "A"):
        return 1.0
    if ch.isupper() or ch.isdigit():
        return 0.62
    return 0.52


def _wide(ch):
    """和文と英数字の空きが入る側の字（漢字・ひらがな・カタカナ）。「〜」「（」などの記号には入らない。"""
    o = ord(ch)
    return 0x3040 <= o <= 0x30FF or 0x3400 <= o <= 0x4DBF or 0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF


def _tokens(text):
    """(幅 em, 先頭の字, 末尾の字)。英数字の続きは 1 語（途中で折り返さない）、和文は 1 字ずつ。"""
    out, word = [], ""
    for ch in text:
        if ch.isascii() and (ch.isalnum() or ch in "._-/:%"):
            word += ch
            continue
        if word:
            out.append(word)
            word = ""
        out.append(ch)
    if word:
        out.append(word)
    return out


def text_em(text):
    """1 行に並べた時の幅（em）。和文と英数字の境目には LibreOffice・PowerPoint が入れる約 1/4 字の空きを足す。"""
    em, prev = 0.0, ""
    for ch in text:
        em += char_w(ch)
        if prev and ((_wide(prev) and ch.isascii() and ch.isalnum()) or (prev.isascii() and prev.isalnum() and _wide(ch))):
            em += 0.25
        prev = ch
    return em


def wrap_lines(text, size, avail):
    """幅 avail（pt）の箱に、字の大きさ size（pt）で流した時の行数。行頭に来られない句読点は前の行にぶら下げる。"""
    n = 0
    for line in text.replace("\v", "\n").split("\n"):
        n += 1
        cur, prev = 0.0, ""
        for tok in _tokens(line):
            w = text_em(tok) * size
            if prev and ((_wide(prev[-1]) and tok[0].isascii() and tok[0].isalnum())
                         or (prev[-1].isascii() and prev[-1].isalnum() and _wide(tok[0]))):
                w += 0.25 * size
            if cur > 0 and cur + w > avail + 0.01 and tok[0] not in NO_LINE_START:
                if w > avail:  # 箱より長い英数字の続きは字で割る
                    n += math.ceil((cur + w) / max(1.0, avail)) - 1
                    cur = (cur + w) % max(1.0, avail)
                else:
                    n += 1
                    cur = 0.0 if tok == " " else w
            else:
                cur += w
            prev = tok
    return max(1, n)


def para_metrics(p, default_size=18.0):
    """python-pptx の段落 → (字の大きさ pt, 行の高さ pt, 1 行で並べた時の幅 pt, 左の字下げ pt, 文字)。"""
    sizes = [r.font.size.pt for r in p.runs if r.font.size]
    size = max(sizes) if sizes else default_size
    ls = p.line_spacing
    if ls is None:
        lsp = size * 1.2
    elif isinstance(ls, float):
        lsp = size * 1.2 * ls
    else:
        lsp = ls.pt
    text = "".join(r.text for r in p.runs)
    marL = p._p.pPr.get("marL") if p._p.pPr is not None else None
    indent = int(marL) / EMU_PT if marL else 0.0
    return size, lsp, text_em(text) * size, indent, text


def cell_height(tbl, ri, ci, cell):
    """1 つのセルの文字が要る高さ（pt、上下の余白込み）。"""
    w = sum(tbl.columns[c].width for c in range(ci, ci + max(1, cell.span_width))) / EMU_PT
    w -= (cell.margin_left + cell.margin_right) / EMU_PT
    h = (cell.margin_top + cell.margin_bottom) / EMU_PT
    for p in cell.text_frame.paragraphs:
        size, lsp, width, ind, text = para_metrics(p, 10)
        if not text:
            continue
        h += wrap_lines(text, size, w - ind) * lsp
    return h


def table_row_heights(tbl):
    """各行の推定の高さ（pt）。宣言した行の高さより低くはならない（PowerPoint の行の高さは最小値）。"""
    out, tall = [], []
    for ri, row in enumerate(tbl.rows):
        need = row.height / EMU_PT
        for ci, cell in enumerate(row.cells):
            if cell.is_spanned:
                continue
            if cell.span_height > 1:
                tall.append((ri, ci, cell))
                continue
            need = max(need, cell_height(tbl, ri, ci, cell))
        out.append(need)
    # 縦に結合したセル: LibreOffice は、結合した行の合計が足りていても、最後の行だけでセルの中身が入る高さまで伸ばす
    # （2026-10-19 実測: 行 50/50/50 でも 80/80/50 でも最後の行が約 107pt に伸びた）。最後の行をその高さにしておく
    for ri, ci, cell in tall:
        last = min(len(out), ri + cell.span_height) - 1
        out[last] = max(out[last], cell_height(tbl, ri, ci, cell))
    return out


def table_growth(shape):
    """(宣言した高さ pt, 推定の高さ pt, 各行の推定 pt)。"""
    tbl = shape.table
    declared = sum(r.height for r in tbl.rows) / EMU_PT
    rows = table_row_heights(tbl)
    return declared, sum(rows), rows


def h_overlap(a, b, min_pt=2.0):
    """2 つの図形が横方向に重なっているか（pt で min_pt より多く）。"""
    if None in (a.left, a.width, b.left, b.width):
        return False
    lo = max(a.left, b.left)
    hi = min(a.left + a.width, b.left + b.width)
    return (hi - lo) / EMU_PT > min_pt


def is_content(sh):
    """重なりを見る相手: 文字のある箱・表。"""
    if getattr(sh, "has_table", False) and sh.has_table:
        return True
    return bool(sh.has_text_frame and sh.text_frame.text.strip())


FOOTER_ZONE = 0.9  # スライドの高さのこの割合より下から始まる物は、下の帯（フッター・ページ番号）として動かさない


def make_room_below_tables(shapes, slide_h, gap_min=4.0):
    """表の行の高さを推定の高さに合わせ、表の下にかぶる物（出典の行など）を下へずらす。

    HTML では表の下の物は流れに沿って置かれる。PowerPoint・LibreOffice で表が伸びた時も同じ並びになるよう、
    伸びた分だけ下の物を動かす。下の帯（フッター）には入れない。戻り値 = 直せなかった重なりの説明（空なら全部直った）。
    """
    from pptx.util import Emu
    notes = []
    tables = sorted((sh for sh in shapes if getattr(sh, "has_table", False) and sh.has_table), key=lambda t: t.top)
    for tb in tables:
        declared, total, rows = table_growth(tb)
        for r, h in zip(tb.table.rows, rows):
            if h * EMU_PT > r.height + EMU_PT * 0.5:
                r.height = Emu(int(math.ceil(h * EMU_PT)))
        top = tb.top / EMU_PT
        bottom = top + total
        others = [o for o in shapes if o is not tb and o.top is not None and o.height is not None and h_overlap(tb, o)
                  and o.top / EMU_PT > top + 2]
        fixed = [o for o in others if o.top / EMU_PT >= slide_h / EMU_PT * FOOTER_ZONE]
        movable = [o for o in others if o not in fixed]
        hit = [o for o in movable if o.top / EMU_PT < bottom + gap_min - 0.5]
        if not hit:
            continue
        first = min(o.top / EMU_PT for o in hit)
        gap0 = first - (top + declared)
        gap = min(12.0, gap0) if gap0 > gap_min else gap_min
        shift = bottom + gap - first
        move = [o for o in movable if o.top / EMU_PT >= first - 0.5]
        limit = min([o.top / EMU_PT for o in fixed] + [slide_h / EMU_PT]) - 2
        lowest = max((o.top + o.height) / EMU_PT for o in move)
        if lowest + shift > limit:
            shift = max(0.0, limit - lowest)
        for o in move:
            o.top = Emu(int(o.top + shift * EMU_PT))
        if first + shift < bottom - 0.5:
            label = next((o.text_frame.text.strip()[:20] for o in hit if o.has_text_frame and o.text_frame.text.strip()), "")
            notes.append(f"表の下の「{label}」を {shift:.0f}pt 下げたが、まだ {bottom - first - shift:.0f}pt 重なる"
                         "（表を短くするか、表の下を空ける）")
    return notes
