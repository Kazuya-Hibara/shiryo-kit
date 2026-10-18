"""shiryo-kit: 確認が要る語（数字・日付・率・金額・法令名・条番号）を文章から拾い、比べられる形（正規形）にする。

check.py ledger が使う。拾い方（references/html-contract.md「出典台帳の形式」と同じ説明）:
  date   2026年4月1日 / 令和8年4月1日（西暦に直して比べる）/ 2026/4/1 / 4月1日 / 4月 / 2026年度 / 14:00
  yen    1,163円 / 3.5万円 / 1億2,000万円（金額に直して比べる: 3.5万円 = 35,000円）
  pct    50% / 50％ / 50パーセント / 5割（= 50%）/ 2.5ポイント
  qty    数 + 単位（人・名・件・社・日・か月・年・時間・分・回・倍・歳・週・枚・台・本・個・点・等級・級 など）
  art    第32条 / 第三十二条 / 第32条の2第1項（漢数字は数字に直す）
  num    単位の無い 3 桁以上の数・カンマ区切りの数・小数（1,200 / 3.5 / 2026）
  law    労働基準法・育児介護休業法施行規則・〜条例・〜政令・〜省令・〜告示・〜通達 などの名前
1〜2 桁の単位なしの数（番号・目次）は拾わない。漢数字（「一人」など）は条番号の中だけ数字に直す。
"""
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

WAREKI = {"令和": 2018, "平成": 1988, "昭和": 1925}
MULT = {"千": Decimal(1000), "万": Decimal(10000), "億": Decimal(10) ** 8, "兆": Decimal(10) ** 12}
UNIT_ALIAS = {"名": "人", "日間": "日", "ヶ月": "か月", "カ月": "か月", "ケ月": "か月", "箇月": "か月", "ヵ月": "か月",
              "ヶ月間": "か月", "か月間": "か月", "カ月間": "か月", "才": "歳", "週間": "週", "時間": "時間", "年間": "年"}
UNITS = ["か月間", "ヶ月間", "カ月間", "か月", "ヶ月", "カ月", "ケ月", "箇月", "ヵ月", "時間", "日間", "週間", "年間",
         "等級", "人", "名", "件", "社", "日", "年", "分", "秒", "回", "倍", "歳", "才", "週", "枚", "台", "本", "個", "点",
         "級", "店舗", "拠点", "世帯", "時限", "単位", "ページ", "頁", "km", "kg", "m2", "㎡"]
UNIT_RE = "|".join(sorted(map(re.escape, UNITS), key=len, reverse=True))
NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
KANJI_DIGITS = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
KANJI_UNITS = {"十": 10, "百": 100, "千": 1000}
KANJI_NUM = r"[〇零一二三四五六七八九十百千]+"
# 「法」で終わっても法令名ではない語
NOT_LAW_SUFFIX = ("方法", "手法", "用法", "技法", "寸法", "文法", "作法", "製法", "療法", "工法", "論法", "話法", "戦法",
                  "魔法", "算法", "説法", "兵法", "仏法", "呼吸法", "対処法", "活用法", "使用法", "解決法", "決法", "考法",
                  "習法", "記法", "書法", "読法", "法令", "違法", "合法", "適法", "不法", "司法", "立法", "遵法", "順法",
                  "脱法", "便法", "秘法", "定法", "製造法", "指導法", "学習法", "評価法", "分析法", "表記法")
NOT_LAW_WORDS = {"就業規則", "社内規則", "社内規程", "賃金規則", "規則", "条例", "通達", "告示", "政令", "省令", "府令"}
LAW_RE = re.compile(r"[一-龥ァ-ヶー・々]{2,30}?(?:法施行規則|法施行令|施行規則|施行令|に関する法律|法律|条例|政令|省令|府令|告示|通達|法)"
                    r"(?:(?=第)|(?![一-龥ァ-ヶ]))")


def kanji_to_int(s):
    """漢数字（〜9999）を数に。読めなければ None。"""
    if not s or not re.fullmatch(KANJI_NUM, s):
        return None
    total, cur = 0, 0
    for ch in s:
        if ch in KANJI_DIGITS:
            cur = cur * 10 + KANJI_DIGITS[ch]  # 「二〇二六」のような並びにも対応
        elif ch in KANJI_UNITS:
            total += (cur or 1) * KANJI_UNITS[ch]
            cur = 0
    return total + cur


def kanji_numerals_to_digits(text):
    """引用（原典の文）の照合用: 漢数字の並びをすべて算用数字に直す（「一日について八時間」→「1日について8時間」）。"""
    def sub(m):
        v = kanji_to_int(m.group(0))
        return str(v) if v is not None else m.group(0)
    return re.sub(KANJI_NUM, sub, text)


def normalize(text):
    t = unicodedata.normalize("NFKC", text or "")
    t = t.replace("〜", "~").replace("–", "-").replace("−", "-")
    # 第三十二条 → 第32条（条・項・号の番号だけ）
    t = re.sub(rf"第({KANJI_NUM})(?=(?:条|項|号))", lambda m: f"第{kanji_to_int(m.group(1))}", t)
    t = re.sub(rf"(?<=条の)({KANJI_NUM})", lambda m: str(kanji_to_int(m.group(1))), t)
    # 範囲「10~20%」「3~5万円」は両側に単位を付けて 2 つの語にする
    t = re.sub(rf"({NUM})\s*~\s*(?=({NUM})\s*([万億千]?\s*(?:円|%|パーセント|割|{UNIT_RE})))",
               lambda m: m.group(1) + m.group(3).replace(" ", "") + "~", t)
    return t


def _dec(s):
    try:
        return Decimal(s.replace(",", ""))
    except InvalidOperation:
        return None


@dataclass(frozen=True)
class Token:
    raw: str
    kind: str
    key: tuple

    def matches(self, other):
        if self.kind != other.kind:
            return False
        if self.kind == "law":
            a, b = self.key[0], other.key[0]
            return a in b or b in a
        if self.kind in ("date", "art"):
            # 片方が欠けた日付（「4月1日」「2026年」）は、ある部分が全部一致すれば同じ
            return all(a is None or b is None or a == b for a, b in zip(self.key, other.key)) and \
                sum(1 for a, b in zip(self.key, other.key) if a is not None and b is not None) >= 1
        return self.key == other.key


def _money(s):
    s = s.replace(" ", "")
    total = Decimal(0)
    for num, unit in re.findall(rf"({NUM})([兆億万千]?)", s):
        v = _dec(num)
        if v is None:
            return None
        total += v * MULT.get(unit, Decimal(1))
    return total


PATTERNS = [
    ("art", re.compile(r"第(\d+)条(?:の(\d+))?(?:第(\d+)項)?(?:第(\d+)号)?")),
    ("art", re.compile(r"第(\d+)(項|号)")),
    ("date-wareki", re.compile(r"(令和|平成|昭和)\s*(\d{1,2}|元)\s*年\s*(?:度)?(?:(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?)?")),
    ("date-ymd", re.compile(r"(?<!\d)(\d{4})\s*年\s*(?:度)?(?:(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?)?")),
    ("date-ymd", re.compile(r"(?<![\d.])(\d{4})[/.\-](\d{1,2})(?:[/.\-](\d{1,2}))?(?![\d])")),
    ("date-md", re.compile(r"(?<![\d.,])(\d{1,2})\s*月\s*(\d{1,2})\s*日")),
    ("date-m", re.compile(r"(?<![\d.,])(\d{1,2})\s*月(?![\d日])")),
    ("time", re.compile(r"(?<![\d])(\d{1,2}):(\d{2})(?![\d])")),
    ("yen", re.compile(rf"((?:(?:{NUM})\s*[兆億万千]\s*)*(?:{NUM})?)\s*円")),
    ("pct", re.compile(rf"({NUM})\s*(%|パーセント|ポイント|pt)")),
    ("pct", re.compile(r"(\d+)\s*割(?:\s*(\d)\s*分)?")),
    ("qty", re.compile(rf"({NUM})\s*([万億千])?\s*({UNIT_RE})")),
    ("num", re.compile(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{3,})(?![\d])")),
]


def extract(text, kinds=None):
    """文章から Token を拾う（重なる時は PATTERNS の先の方を採る）。"""
    t = normalize(text)
    used = [False] * (len(t) + 1)
    out = []

    def free(a, b):
        return not any(used[a:b])

    def take(a, b):
        for i in range(a, b):
            used[i] = True

    for kind, rx in PATTERNS:
        for m in rx.finditer(t):
            a, b = m.span()
            if a == b or not free(a, b):
                continue
            key = None
            g = m.groups()
            if kind == "art":
                if len(g) == 2 and g[1] in ("項", "号"):
                    key = ("art-" + g[1], int(g[0]))
                else:
                    key = tuple(int(x) if x else None for x in g)
            elif kind.startswith("date"):
                iv = lambda x: int(x) if x else None  # noqa: E731
                if kind == "date-wareki":
                    key = (WAREKI[g[0]] + (1 if g[1] == "元" else int(g[1])), iv(g[2]), iv(g[3]))
                elif kind == "date-ymd":
                    key = (int(g[0]), iv(g[1]), iv(g[2]))
                elif kind == "date-md":
                    key = (None, int(g[0]), int(g[1]))
                else:
                    key = (None, int(g[0]), None)
                if key[1] is not None and not 1 <= key[1] <= 12:
                    continue
                if key[2] is not None and not 1 <= key[2] <= 31:
                    continue
                kind = "date"
            elif kind == "time":
                key = (int(g[0]), int(g[1]))
            elif kind == "yen":
                if not re.search(r"\d", g[0] or ""):
                    continue
                v = _money(g[0])
                if v is None:
                    continue
                key = (v.normalize(),)
            elif kind == "pct":
                if len(g) == 2 and g[1] in ("%", "パーセント"):
                    key = ("%", _dec(g[0]).normalize())
                elif len(g) == 2 and g[1] in ("ポイント", "pt"):
                    key = ("pt", _dec(g[0]).normalize())
                else:
                    key = ("%", (Decimal(g[0]) * 10 + (Decimal(g[1]) if g[1] else 0)).normalize())
            elif kind == "qty":
                v = _dec(g[0])
                if v is None:
                    continue
                v = v * MULT.get(g[1] or "", Decimal(1))
                unit = UNIT_ALIAS.get(g[2], g[2])
                key = (unit, v.normalize())
            elif kind == "num":
                v = _dec(g[0])
                if v is None:
                    continue
                key = (v.normalize(),)
            if kinds and kind not in kinds:
                take(a, b)
                continue
            take(a, b)
            out.append(Token(m.group(0).strip(), kind, key))
    if not kinds or "law" in kinds:
        for m in LAW_RE.finditer(t):
            name = m.group(0)
            # 「〜の」「〜は」で始まる取りすぎを避けるため、先頭のひらがなは含めない（正規表現が漢字・カナだけ）
            if name in NOT_LAW_WORDS or name.endswith(NOT_LAW_SUFFIX) or len(name) < 3:
                continue
            out.append(Token(name, "law", (name,)))
    return out


def law_in_text(name, text):
    return name in re.sub(r"\s+", "", normalize(text))
