"""shiryo-kit: HTML デッキの <style> を標準ライブラリだけで読む、小さな CSS の読み手。

ブラウザを使わない書き出し（html_to_pptx_static.py）と、静的な読み取り（deck_html.py の「見えない文字」の判定）が使う。
対応: タグ・.class・#id・:not(.x)・:root・:first-child・:last-child・[属性] の組み合わせ、子孫（空白）と子（>）の結合、
変数（--x と var(--x)。当たる要素から子へ受け継ぐ。:root・html の値が文書の既定）、詳細度の順。@media・@page などの @ の塊と、対応しない書き方（:has・::before など）の規則は読まない。
"""
import re

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_SIMPLE = re.compile(r"(?P<tag>^[a-zA-Z][a-zA-Z0-9-]*|^\*)?(?P<rest>.*)$")
_PART = re.compile(r"\.(?P<cls>[\w-]+)|#(?P<id>[\w-]+)|:not\(\.(?P<not>[\w-]+)\)|:(?P<pseudo>first-child|last-child)"
                   r"|:(?P<root>root)\b|\[(?P<attr>[\w-]+)(?:=\"?(?P<val>[^\]\"]*)\"?)?\]")


class Rule:
    __slots__ = ("chain", "decls", "spec", "order")

    def __init__(self, chain, decls, spec, order):
        self.chain, self.decls, self.spec, self.order = chain, decls, spec, order


def _compound(s):
    """'td.ax:not(.x)' → dict。対応しない書き方なら None。"""
    m = _SIMPLE.match(s)
    tag = (m.group("tag") or "").lower()
    rest = m.group("rest")
    c = {"tag": "" if tag == "*" else tag, "cls": [], "id": [], "not": [], "pseudo": [], "attr": [], "root": False}
    pos = 0
    while pos < len(rest):
        pm = _PART.match(rest, pos)
        if not pm:
            return None
        for k in ("cls", "id", "not", "pseudo"):
            if pm.group(k):
                c[k].append(pm.group(k))
        if pm.group("root"):
            c["root"] = True
        if pm.group("attr"):
            c["attr"].append((pm.group("attr"), pm.group("val")))
        pos = pm.end()
    return c


def _selector(sel):
    """'.a > .b .c' → [(結合子, compound), …]（右端が対象）。対応しなければ None。"""
    sel = re.sub(r"\s*>\s*", " > ", sel.strip())
    toks = sel.split()
    chain, comb = [], " "
    for t in toks:
        if t == ">":
            comb = ">"
            continue
        c = _compound(t)
        if c is None:
            return None
        chain.append((comb, c))
        comb = " "
    if not chain:
        return None
    spec = (sum(len(c["id"]) for _, c in chain),
            sum(len(c["cls"]) + len(c["not"]) + len(c["pseudo"]) + len(c["attr"]) + c["root"] for _, c in chain),
            sum(1 for _, c in chain if c["tag"]))
    return chain, spec


def parse_decls(body):
    out = {}
    for d in body.split(";"):
        if ":" not in d:
            continue
        k, v = d.split(":", 1)
        k = k.strip().lower()
        v = re.sub(r"\s*!important\s*$", "", v.strip())
        if k:
            out[k] = v
    return out


def _is_document(chain):
    """:root・html だけの selector（文書全体の既定の変数を置く所）。"""
    return len(chain) == 1 and (chain[0][1]["root"] or chain[0][1]["tag"] == "html") and not any(
        chain[0][1][k] for k in ("cls", "id", "not", "pseudo", "attr"))


def parse_css(text):
    """CSS 文字列 → [Rule]（詳細度・出現順で並べたもの）と 文書の既定の変数（:root・html の規則の --x）の辞書。
    .skin-cool{--navy:…} のように要素に当たって初めて効く変数は、ここには入れない（cascade が当たる要素から受け継がせる）。"""
    text = _COMMENT.sub("", text)
    rules, variables, order = [], {}, 0
    i, n = 0, len(text)
    while i < n:
        j = text.find("{", i)
        if j < 0:
            break
        head = text[i:j].strip()
        if head.startswith("@"):  # @media・@page など: 中の { } ごと飛ばす
            depth, k = 1, j + 1
            while k < n and depth:
                depth += {"{": 1, "}": -1}.get(text[k], 0)
                k += 1
            i = k
            continue
        k = text.find("}", j)
        if k < 0:
            break
        decls = parse_decls(text[j + 1:k])
        i = k + 1
        for sel in head.split(","):
            parsed = _selector(sel)
            if parsed is None:
                continue
            order += 1
            rules.append(Rule(parsed[0], decls, parsed[1], order))
    rules.sort(key=lambda r: (r.spec, r.order))
    for r in rules:
        if _is_document(r.chain):
            variables.update({k: v for k, v in r.decls.items() if k.startswith("--")})
    return rules, variables


def _match_compound(c, node):
    if c["tag"] and node.tag != c["tag"]:
        return False
    if c["root"] and node.tag != "html":
        return False
    cls = node.classes
    if any(x not in cls for x in c["cls"]) or any(x in cls for x in c["not"]):
        return False
    if any(node.attrs.get("id") != x for x in c["id"]):
        return False
    for a, v in c["attr"]:
        if a not in node.attrs or (v is not None and node.attrs.get(a) != v):
            return False
    for p in c["pseudo"]:
        flag = getattr(node, "first" if p == "first-child" else "last", None)
        if not flag:  # 分からない時（流しながら読む時の last-child）は当てない
            return False
    return True


def matches(chain, node):
    comb, c = chain[-1]
    if not _match_compound(c, node):
        return False
    rest = chain[:-1]
    if not rest:
        return True
    anc = node.parent
    if comb == ">":
        return anc is not None and matches(rest, anc)
    while anc is not None:
        if matches(rest, anc):
            return True
        anc = anc.parent
    return False


def resolve_var(v, variables, depth=0):
    if "var(" not in v or depth > 8:
        return v

    def rep(m):
        name, fb = m.group(1).strip(), (m.group(2) or "").strip()
        return variables.get(name, fb)
    return resolve_var(re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\))?[^()]*))?\)", rep, v), variables, depth + 1)


def cascade(rules, variables, node, inherited=None):
    """node に当たる宣言を詳細度の順に重ねた辞書（style 属性が最後）と、node で効いている変数。
    変数は親の変数（inherited。根では文書の既定 variables）に、node に当たる規則の --x を重ねたもの。子へ渡す。"""
    out = {}
    for r in rules:
        if matches(r.chain, node):
            out.update(r.decls)
    if node.attrs.get("style"):
        out.update(parse_decls(node.attrs["style"]))
    parent = variables if inherited is None else inherited
    own = dict(parent)
    # 変数の中の var() は、宣言した要素で解く（:root{--b:var(--a)} は :root の --a。子で --a を変えても --b は変わらない）
    own.update({k: resolve_var(v, parent) for k, v in out.items() if k.startswith("--")})
    return {k: resolve_var(v, own) for k, v in out.items() if not k.startswith("--")}, own


def computed(rules, variables, node, inherited=None):
    return cascade(rules, variables, node, inherited)[0]


def is_hidden(decls):
    d = decls.get("display", "").strip().lower()
    v = decls.get("visibility", "").strip().lower()
    return d == "none" or v in ("hidden", "collapse")


def style_text(html):
    """<style> の中身。HTML のコメントの中の「<style>」の字は数えない（部品集の冒頭の説明文など）。"""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", html, flags=re.S | re.I))


# ---------------------------------------------------------------- 値
NAMED = {"white": "#ffffff", "black": "#000000", "red": "#ff0000", "gray": "#808080", "grey": "#808080",
         "transparent": None, "none": None}


def color(v):
    """CSS の色 → '#rrggbb'（透明・読めない時は None）。"""
    if not v:
        return None
    v = v.strip().lower()
    m = re.search(r"#([0-9a-f]{3,8})\b", v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h[:3])
        return "#" + h[:6]
    m = re.search(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+%?))?", v)
    if m:
        a = m.group(4)
        if a is not None and float(a.rstrip("%")) == 0:
            return None
        return "#" + "".join(f"{min(255, int(float(x))):02x}" for x in m.groups()[:3])
    for word in v.replace(",", " ").split():
        if word in NAMED:
            return NAMED[word]
    return None


def length_pt(v, base_pt=12.0, container=None):
    """'11.5pt' '18px' '4mm' '1.2em' '120%' → pt（読めなければ None）。スライド 960pt = 338.67mm = 1280px の換算。
    % は container（含む箱の幅・高さ pt）があればその割合、無ければ字の大きさの割合（font-size の %）。"""
    if v is None:
        return None
    if container is not None and str(v).strip().endswith("%"):
        try:
            return float(str(v).strip()[:-1]) / 100 * container
        except ValueError:
            return None
    m = re.match(r"^\s*(-?[\d.]+)\s*(pt|px|mm|cm|in|em|rem|%)?\s*$", str(v))
    if not m:
        return None
    x, u = float(m.group(1)), (m.group(2) or "px")
    return {"pt": x, "px": x * 0.75, "mm": x * 72 / 25.4, "cm": x * 720 / 25.4, "in": x * 72,
            "em": x * base_pt, "rem": x * 12.0, "%": x / 100 * base_pt}[u]
