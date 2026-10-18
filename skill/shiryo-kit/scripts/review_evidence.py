"""shiryo-kit: 検品の独立の記録（review/independence-<n>.json）と結果（review/review-<n>.md）を確かめる。

check.py review-evidence / check.py manifest が使う。記録は review_record.py が書く（形は references/html-contract.md）。
作り手の「点検しました」は証拠にしない: 記録・時刻・file の sha256 が揃わなければ「未検品」。
"""
import datetime
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA = "shiryo-kit/review-independence/v1"
METHODS = ("subagent", "fresh-process")
INPUT_KEYS = {"brief", "ledger", "deck"}
SLACK_BEFORE = datetime.timedelta(seconds=5)     # 結果の file の更新時刻の許容（時計の丸め）
SLACK_AFTER = datetime.timedelta(seconds=120)    # finish を打つまでの遅れ
FUTURE = datetime.timedelta(minutes=2)
MIN_DURATION = datetime.timedelta(seconds=20)   # これより短い検品は WARN（原典を開き直す点検は数分かかる）
VERDICT = re.compile(r"結論\s*[:：]?\s*\**\s*(合格|直しが必要)")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ts(s):
    if not isinstance(s, str) or not s:
        return None
    try:
        t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.astimezone()


@dataclass
class RoundResult:
    n: int
    fails: list = field(default_factory=list)
    warns: list = field(default_factory=list)
    record: dict = field(default_factory=dict)
    verdict: str = ""

    @property
    def ok(self):
        return not self.fails


def rounds(review_dir):
    out = set()
    for p in Path(review_dir).glob("*-*.*"):
        m = re.fullmatch(r"(?:independence|review|request)-(\d+)\.(?:json|md)", p.name)
        if m:
            out.add(int(m.group(1)))
    return sorted(out)


def check_round(review_dir, n, now=None):
    d = Path(review_dir)
    case = d.resolve().parent
    now = now or datetime.datetime.now().astimezone()
    r = RoundResult(n)
    rec_path = d / f"independence-{n}.json"
    if not rec_path.exists():
        r.fails.append(f"{n} 巡目: 独立の記録 {rec_path.name} が無い（review_record.py で起動を記録していない）")
        return r
    try:
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
    except ValueError as e:
        r.fails.append(f"{n} 巡目: {rec_path.name} が JSON として読めない（{e}）")
        return r
    if not isinstance(rec, dict):
        r.fails.append(f"{n} 巡目: {rec_path.name} の中身が JSON の object でない")
        return r
    r.record = rec
    F = r.fails.append
    if rec.get("schema") != SCHEMA:
        F(f"{n} 巡目: schema が「{rec.get('schema')}」（{SCHEMA} であること）")
    if rec.get("round") != n:
        F(f"{n} 巡目: 記録の round が {rec.get('round')}（file 名と違う）")
    method = rec.get("method")
    if method not in METHODS:
        F(f"{n} 巡目: method が「{method}」（subagent か fresh-process。同じ会話の続きでの点検は検品ではない）")
    if rec.get("status") != "finished":
        F(f"{n} 巡目: 記録の status が「{rec.get('status')}」（reviewer が最後まで終わっていない）")
    st, en = _ts(rec.get("started_at")), _ts(rec.get("ended_at"))
    if st is None or en is None:
        F(f"{n} 巡目: 起動・終了の時刻が無いか読めない（started_at / ended_at）")
    else:
        if not st < en:
            F(f"{n} 巡目: 終了の時刻が起動の時刻より前（{rec.get('started_at')} → {rec.get('ended_at')}）")
        elif en - st < MIN_DURATION:
            r.warns.append(f"{n} 巡目: reviewer の起動から終了まで {(en - st).total_seconds():.1f} 秒（検品にしては短すぎる。中身を確かめる）")
        if en > now + FUTURE or st > now + FUTURE:
            F(f"{n} 巡目: 時刻が未来になっている（{rec.get('ended_at')}）")
    if not str(rec.get("reviewer_id") or "").strip():
        F(f"{n} 巡目: reviewer の識別子（subagent の id / 別プロセスの pid）が無い")
    ex = rec.get("exit_status")
    if method == "fresh-process":
        if ex != 0:
            F(f"{n} 巡目: 別プロセスの終了コードが {ex}（0 でない）")
        if not isinstance(rec.get("pid"), int):
            F(f"{n} 巡目: 別プロセスの pid が無い（review_record.py run で起動していない）")
        run = d / str(rec.get("run_file") or f"run-{n}.jsonl")
        if not run.exists():
            F(f"{n} 巡目: 別プロセスの実行記録 {run.name} が無い")
        elif rec.get("run_sha256") != sha256(run):
            F(f"{n} 巡目: 実行記録 {run.name} が記録の後に変わった（sha256 が違う）")
        elif run.stat().st_size == 0:
            F(f"{n} 巡目: 実行記録 {run.name} が空")
    elif method == "subagent":
        if ex not in (0, None):
            F(f"{n} 巡目: subagent の終了コードが {ex}")
        if ex is None and not rec.get("exit_note"):
            F(f"{n} 巡目: 終了コードが無く、その理由（exit_note）も無い")
        if rec.get("transcript"):
            t = Path(rec["transcript"])
            if t.exists() and rec.get("transcript_sha256") != sha256(t):
                F(f"{n} 巡目: subagent の実行記録 {t.name} が記録の後に変わった")
    # 渡した物: BRIEF・台帳・スライドの 3 つだけ。今の file と sha256 が同じこと
    inputs = rec.get("inputs") or {}
    hashes = rec.get("inputs_sha256") or {}
    if not isinstance(inputs, dict) or set(inputs) != INPUT_KEYS:
        F(f"{n} 巡目: 渡した物（inputs）が brief・ledger・deck の 3 つでない（{sorted(inputs) if isinstance(inputs, dict) else inputs}）")
    else:
        for k in sorted(INPUT_KEYS):
            f = (case / inputs[k]) if not Path(inputs[k]).is_absolute() else Path(inputs[k])
            if not f.exists():
                F(f"{n} 巡目: 検品に渡した {inputs[k]} が今は無い")
            elif hashes.get(k) != sha256(f):
                F(f"{n} 巡目: 検品の後に {inputs[k]} が変わった（今の版は検品していない）")
    req = d / str(rec.get("request_file") or f"request-{n}.md")
    if not req.exists():
        F(f"{n} 巡目: 依頼文 {req.name} が無い")
    elif rec.get("request_sha256") != sha256(req):
        F(f"{n} 巡目: 依頼文 {req.name} が起動の後に書き換えられた")
    else:
        rt = req.read_text(encoding="utf-8", errors="replace")
        if isinstance(inputs, dict):
            for k in sorted(INPUT_KEYS & set(inputs)):
                if Path(inputs[k]).name not in rt:
                    r.warns.append(f"{n} 巡目: 依頼文に {Path(inputs[k]).name} の path が無い")
    # 結果の file: 起動〜終了の間に書かれ、その後書き換えられていない
    res = d / str(rec.get("result_file") or f"review-{n}.md")
    if not res.exists():
        F(f"{n} 巡目: 検品の結果 {res.name} が無い")
        return r
    if rec.get("result_sha256") != sha256(res):
        F(f"{n} 巡目: 検品の結果 {res.name} が記録の後に書き換えられた（sha256 が違う）")
    mt = datetime.datetime.fromtimestamp(res.stat().st_mtime).astimezone()
    if st is not None and en is not None and not (st - SLACK_BEFORE <= mt <= en + SLACK_AFTER):
        F(f"{n} 巡目: 結果 {res.name} の更新時刻 {mt.isoformat(timespec='seconds')} が reviewer の起動〜終了の間でない")
    text = res.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        F(f"{n} 巡目: 結果 {res.name} が空")
        return r
    line = next((ln for ln in text.splitlines() if VERDICT.search(ln)), None)
    if line is None:
        F(f"{n} 巡目: 結果に「結論: 合格」か「結論: 直しが必要」の行が無い")
    elif "合格" in line and "直しが必要" in line:
        F(f"{n} 巡目: 結論の行が雛形のまま（合格 / 直しが必要 のどちらかにする）")
    else:
        r.verdict = VERDICT.search(line).group(1)
    if not re.search(r"(?m)^\s*spec_rev\s*[:：]\s*\S+", text):
        r.warns.append(f"{n} 巡目: 結果の最後に spec_rev の行が無い")
    if isinstance(hashes, dict) and hashes.get("deck"):
        hexes = set(h.lower() for h in re.findall(r"\b[0-9a-fA-F]{8,64}\b", text))
        if not any(hashes["deck"].startswith(h) for h in hexes):
            r.warns.append(f"{n} 巡目: reviewer が点検した deck の sha256 を結果に書いていない（または今の deck と違う）")
    return r


def check_review_dir(review_dir, now=None):
    """(最後の巡の RoundResult か None, それより前の巡の結果のリスト, 全体の FAIL 理由)。"""
    d = Path(review_dir)
    if not d.is_dir():
        return None, [], [f"検品のフォルダ {review_dir} が無い"]
    ns = rounds(d)
    if not ns:
        return None, [], [f"{review_dir} に検品の記録が無い（request-<n>.md・review-<n>.md・independence-<n>.json）"]
    results = [check_round(d, n, now) for n in ns]
    return results[-1], results[:-1], []
