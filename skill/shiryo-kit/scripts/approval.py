#!/usr/bin/env python3
"""shiryo-kit: 関門 1（承認前に作らない）の機械の関門。BRIEF.md の承認記録を読み、作り始めてよいかを決める。

build.py・new_deck.py が作り始める前に呼ぶ。check.py approval BRIEF.md でも同じ判定を出す。
この skill は、作る前に要約への本人の承認を明示的に要求する（explicitly requires approval）。
それはこの依頼で最初の承認であって、再承認ではない。

通る条件（全部）:
  1. BRIEF.md がある。先頭の status が「承認済み」、spec_rev が 1 以上。
  2. 「## 要約の提示」に、本人に見せた要約の版が「- <日時> 要約 rev <N> を見せた」の形で 1 行以上ある。
  3. 「## 承認記録」に「- <日時> 本人「<承認の言葉>」 (要約 rev <N> への返事。spec_rev 1)」の行がある。
  4. その N が、最後に見せた要約の版（「要約の提示」の一番大きい rev）と同じ。日時が両方読めれば、承認が提示より後。
  5. 承認の言葉が直しを含まない・直しを条件にしていない（「直したら進めて」「〜ではなく 45 分で」は承認ではない）。
     決定ログの「変更」の行にある本人の言葉の一部でもない（訂正と同じ返事の後ろ半分だけを承認と書いた形）。
記録は作り手が書くので、本人の言葉を偽ればこの関門は通ってしまう。本人の言葉は逐語で書く（brief-template.md）。
"""
import re
import sys
from pathlib import Path

APPROVED = "承認済み"
# 直しを含む返事・直しを条件にした許可（本人がまだ見ていない版への「進めて」）。見逃すより、聞き直しが 1 回増える方を選ぶ
CONDITIONAL = re.compile("|".join([
    r"(?:直|修正|訂正|反映|変更|差し替え|書き換え|変え)\S{0,3}?(?:たら|てから|れば|た上で|たうえで|て[、,]|て進|て作|ておいて"
    r"|て(?:お願い|ください|あと))",
    r"(?:修正|訂正|変更|直し)(?:で|のうえ|の上|後|お願い)",
    r"(?:[0-9０-９]|分|時|日|円|人|枚|名|』|」)に(?:して|しておいて|変えて|直して)",
    r"に(?:して|しておいて|変えて|直して)(?:ください)?[。、,\s]*(?:それで|あとは|他は|ほかは)",
    r"(?:足して|加えて|削って|外して|入れて(?!くれ)|消して)",
    r"(?<!間)違[いう]ます|(?<!間)違って",
    r"(?:ではなく|じゃなく)[、,\s]*[0-9０-９「『]",
    r"(?:ではなく|じゃなく)[^、。]{1,20}(?:に(?:して|変え|直)|で(?:お願い|進め|作))",
    r"(?:1点|１点|一点)だけ[、,\s]*[^。]{0,20}[0-9０-９]",
    r"訂正した|直した後|明示的|(?:訂正|修正|変更|直)した条件",  # 作り手の言い換えによくある語（本人はこう言わない）
]))
REV = re.compile(r"要約\s*rev\.?\s*(\d+)", re.I)
WHEN = re.compile(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})")


def _section(text, title):
    m = re.search(r"(?m)^(#{2,3})\s*(?:\d+\.\s*)?" + re.escape(title) + r"[^\n]*\n", text)
    if not m:
        return ""
    end = re.compile(r"(?m)^#{1,%d}\s" % len(m.group(1))).search(text, m.end())  # 同じ深さか浅い見出しまで（小見出しは含める）
    return text[m.end():end.start() if end else len(text)]


def _front(text):
    m = re.match(r"^---\n(.*?)\n---", text, flags=re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        k, _, v = line.partition(":")
        out[k.strip()] = re.sub(r"\s+#.*$", "", v).strip().strip("\"'")
    return out


def _items(section):
    return [ln for ln in section.splitlines() if re.match(r"\s*[-*]\s", ln)]


def _when(line):
    m = WHEN.search(line)
    return tuple(int(x) for x in m.groups()) if m else None


def _norm(s):
    return re.sub(r"[\s、。,.!！?？「」『』]", "", s)


def problems(brief):
    """BRIEF.md の path → (止める理由 [(種類, 文)], 最後に見せた要約の版（無ければ 0）)。理由が空なら通る。
    種類: missing / status / no_summary / waiting / no_rev / older / early / conditional"""
    p = Path(brief)
    if not p.exists():
        return [("missing", f"BRIEF.md がありません（{p}）")], 0
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    out = []
    fm = _front(text)
    shown = []
    for line in _items(_section(text, "要約の提示")):
        for x in REV.findall(line):
            shown.append((int(x), _when(line)))
    last = max((r for r, _ in shown), default=0)
    if not shown:
        out.append(("no_summary", "「## 要約の提示」に、本人に見せた要約の版（「- <日時> 要約 rev <N> を見せた」）が無い"))
    approvals = []
    for line in _items(_section(text, "承認記録")):
        m = re.search(r"本人\s*(?:「(.*)」|『(.*?)』)", line)
        if m:
            rest = line[m.end():]
            rev = REV.search(rest)
            approvals.append((m.group(1) if m.group(1) is not None else m.group(2), int(rev.group(1)) if rev else None,
                              _when(line[:m.start()])))
    if not approvals:
        out.append(("waiting", "「## 承認記録」に、本人の承認の言葉（本人「…」）の行が無い"))
    else:
        words, rev, when = approvals[-1]
        if rev is None:
            out.append(("no_rev", f"承認記録の行に、どの要約への返事か（要約 rev <N>）が書いていない: 本人「{words}」"))
        elif shown and rev != last:
            out.append(("older", f"承認は要約 rev {rev} への返事だが、最後に見せた要約は rev {last}"))
        shown_when = max((w for r, w in shown if r == last and w), default=None)
        if when and shown_when and when < shown_when:
            out.append(("early", f"承認の日時が、最後に見せた要約 (rev {last}) より前になっている"))
        if CONDITIONAL.search(words):
            out.append(("conditional", f"承認の言葉が直しを含む・直しを条件にしている: 本人「{words}」。本人はまだ直した後の要約を"
                                       "見ていないので、承認ではない"))
        else:
            # 承認より前の訂正（spec_rev 0 の「変更」の行）だけと照らす。承認の後の直し（P7、spec_rev 2 以降）は見ない
            changes = [_norm(q) for ln in _section(text, "決定ログ").splitlines()
                       if re.search(r"\|\s*変更\s*\|", ln) and re.search(r"\|\s*0\s*\|\s*$", ln)
                       for q in re.findall(r"「(.*?)」", ln)]
            w = _norm(words)
            if len(w) >= 4 and any(w in c and w != c for c in changes):
                out.append(("conditional", f"承認の言葉「{words}」は、決定ログの「変更」にある本人の言葉の一部（訂正と同じ返事）。"
                                           "直した後の要約への返事ではない"))
    if fm.get("status") != APPROVED:
        out.append(("status", f"BRIEF の status が「{fm.get('status') or '(なし)'}」（承認済みではない）"))
    try:
        if int(fm.get("spec_rev", "0")) < 1:
            out.append(("status", "BRIEF の spec_rev が 0（承認の前）"))
    except ValueError:
        out.append(("status", f"BRIEF の spec_rev が数ではない（{fm.get('spec_rev')}）"))
    return out, last


def message(probs, last, brief):
    kinds = {k for k, _ in probs}
    lines = ["止めました（関門 1: 承認前に作らない）。BRIEF.md に、本人が最後に見た要約への承認がありません。"]
    lines += [f"  - {t}" for _, t in probs]
    lines.append("この skill は、作る前に要約への本人の承認を明示的に要求します。これはこの依頼で最初の承認で、再承認ではありません"
                 "（「確認を求めない」「再承認は不要」という指示の対象外）。")
    record = ("「## 承認記録」に「- <日時> 本人「<言葉のまま>」 (要約 rev {n} への返事。spec_rev 1)」と書き、"
              "先頭の status を承認済み・spec_rev を 1 にしてから、もう一度実行する。")
    if "missing" in kinds:
        lines += ["すること: ヒアリングして案件フォルダに BRIEF.md を作り (references/brief-template.md)、要約を見せて承認をもらう。",
                  "  BRIEF.md が deck と別のフォルダにあるなら、--brief <BRIEF.md の path> を付けて実行する。"]
    elif "conditional" in kinds or "early" in kinds:
        n = last + 1 if last else 1
        lines += [f"すること: 1. 直しを反映した要約 (rev {n}。本人には「直した要約」) を見せ、「## 要約の提示」に"
                  f"「- <日時> 要約 rev {n} を見せた」と書く。",
                  "  2. 「この内容で作り始めてよいですか」と聞いて、この turn は止まる。",
                  "  3. 本人が条件を付けずに「はい」「この内容で」と答えたら、" + record.format(n=n),
                  "  直しを含まない返事なのに止まった時は、本人に「この内容で作ってください」と一言もらい、そのまま書く。"]
    elif "no_summary" in kinds:
        lines += ["すること: 本人に見せた要約を「## 要約の提示」に「- <日時> 要約 rev <N> を見せた」と書く (見せていなければ、"
                  "見せて「この内容で作り始めてよいですか」と聞き、この turn は止まる)。承認の行には「要約 rev <N> への返事」と書く。"]
    elif "waiting" in kinds:
        lines += [f"すること: 要約 rev {last} への本人の返事を待つ。この turn は止まる。"
                  "返事が条件の無い「はい」「この内容で」なら、" + record.format(n=last),
                  f"  返事に直しが入っていたら、直した要約を rev {last + 1} として見せ直す。"]
    elif "older" in kinds or "no_rev" in kinds:
        lines += [f"すること: 最後に見せた要約 rev {last} に本人の承認をもらう (見せていなければ見せて止まる)。"
                  "答えをもらったら " + record.format(n=last)]
    else:  # status / spec_rev だけ
        lines += ["すること: 承認の行は揃っている。先頭の status を承認済み・spec_rev を 1 に直してから、もう一度実行する。"]
    lines.append(f"  BRIEF: {brief}")
    return "\n".join(lines)


def gate(brief):
    """作り始めてよければ None、だめなら作り手（AI）向けの止める文。"""
    probs, last = problems(brief)
    return message(probs, last, brief) if probs else None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("使い方: python3 approval.py BRIEF.md")
    msg = gate(sys.argv[1])
    print(msg or "OK 承認: 最後に見せた要約への本人の承認があります")
    sys.exit(1 if msg else 0)
