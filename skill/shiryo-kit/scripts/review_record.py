#!/usr/bin/env python3
"""shiryo-kit: 別の文脈で行った検品（P5）の「独立の記録」を、進行役の手書きではなく script が書く。

check.py review-evidence / check.py manifest がこの記録を読む（形は references/html-contract.md「独立の記録」）。

使い方（案件フォルダで。review/ は案件フォルダの直下）:
  # subagent で検品する時: 起動の直前に start、返事が返った直後に finish
  python3 review_record.py start  review --round 1 --method subagent
  python3 review_record.py finish review --round 1 --reviewer-id <subagent の id> [--exit 0] [--transcript <実行記録の file>]

  # 別プロセス（codex exec / claude -p）で検品する時: run が起動・時刻・pid・終了コード・出力を全部記録する
  python3 review_record.py run review --round 1 --stdin review/request-1.md -- codex exec --json --skip-git-repo-check -C . -s workspace-write -m gpt-6-astra -c model_reasoning_effort="high" -o review/last-1.md -

  python3 review_record.py show review --round 1      # 記録を表示

記録するもの（review/independence-<n>.json）:
  method（subagent / fresh-process）・started_at / ended_at（この script が時計から取る）・inputs（BRIEF.md・ledger.md・deck.html の
  3 つ。配布物は --extra handout.html で extra_inputs に足す）と start の時点の sha256・依頼文 review/request-<n>.md の sha256・reviewer_id・exit_status・結果 review/review-<n>.md の
  sha256 と更新時刻・run の時は pid と出力（review/run-<n>.jsonl）の sha256。
start の前に review/request-<n>.md を書いておく（無いと止まる。references/review.md の雛形に無い行があっても止まる）。
finish は review/review-<n>.md が無いと止まる。
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "shiryo-kit/review-independence/v1"
RECORDER = "shiryo-kit/scripts/review_record.py"
INPUT_NAMES = {"brief": "BRIEF.md", "ledger": "ledger.md", "deck": "deck.html"}
TEMPLATE_DOC = Path(__file__).resolve().parent.parent / "references" / "review.md"
CODEX_ENV_KEYS = ("CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED", "CODEX_THREAD_ID")


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def paths(review_dir, n):
    d = Path(review_dir)
    return {
        "record": d / f"independence-{n}.json",
        "request": d / f"request-{n}.md",
        "result": d / f"review-{n}.md",
        "run": d / f"run-{n}.jsonl",
        "stderr": d / f"run-{n}.stderr.log",
    }


def case_dir(review_dir):
    return Path(review_dir).resolve().parent


def die(msg):
    sys.exit(f"review_record: {msg}")


def load(review_dir, n):
    p = paths(review_dir, n)["record"]
    if not p.exists():
        die(f"{p} が無い（先に start を実行する）")
    return json.loads(p.read_text(encoding="utf-8"))


def save(review_dir, n, rec):
    p = paths(review_dir, n)["record"]
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


# 雛形の埋め字ごとに、入ってよい物の形（作り手の観点を埋め字に紛れ込ませないため）
_PATH = r"[^。、「」\n]+?"
_FILE = r"[^\s。、「」（）()]+\.[A-Za-z0-9]+"
SLOTS = {
    "<n>": r"\d+",
    "<BRIEF の spec_rev をそのまま>": r"\d+",
    "<案件フォルダ>": _PATH,
    "<skill>": _PATH,
    "<案件>": r"[^。、「」\n]+?",
    "<名前>": r"[^\s/\\。、「」]+",
    "<ほかの成果物>": rf"(?:{_FILE}(?:\s+{_FILE})*)?",
    "<配布物の HTML>": _FILE,
}


def _literal(text):
    """雛形の地の文: 空白の数は問わず、/ は Windows の \\ でもよい。"""
    return re.escape(text).replace(r"\ ", r"\s*").replace("/", r"[\\/]")


def _template_patterns(names=None):
    """references/review.md の依頼文の雛形の各行を正規表現にする（<…> は SLOTS の形、/ は \\ も可）。
    names = {"BRIEF.md": 実際の名前, …}（--brief 等で別の名前を渡した時）。"""
    try:
        doc = TEMPLATE_DOC.read_text(encoding="utf-8")
    except OSError as e:
        die(f"依頼文の雛形 {TEMPLATE_DOC} が読めない（{e}）")
    m = re.search(r"## reviewer への依頼文.*?```markdown\n(.*?)\n```", doc, re.S)
    if not m:
        die(f"{TEMPLATE_DOC} に依頼文の雛形が見つからない")
    pats = []
    for line in m.group(1).splitlines():
        line = " ".join(line.split())
        if not line:
            continue
        for default, actual in (names or {}).items():
            line = line.replace(default, actual)
        # 当てはまらない物は消してよい（pptx が無い時の「・out/ の file」）。書き換えは認めない
        for variant in {line, line.replace("・out/ の file", "")}:
            out, pos = [], 0
            for mm in re.finditer(r"<[^<>]*>", variant):
                out.append(_literal(variant[pos:mm.start()]))
                out.append(SLOTS.get(mm.group(0), r"[^\n]+?"))
                pos = mm.end()
            out.append(_literal(variant[pos:]))
            pats.append(re.compile("".join(out)))
    return pats


def request_deviations(request_file, names=None):
    """依頼文の中で、雛形のどの行にも当てはまらない行（作り手の観点・説明が reviewer に移る所）と、埋めていない <…>。"""
    pats = _template_patterns(names)
    out = []
    for line in Path(request_file).read_text(encoding="utf-8", errors="replace").splitlines():
        s = " ".join(line.split())
        if not s:
            continue
        if re.search(r"<[^<>]*>", s):
            out.append(f"{s}  ← <…> を埋めていない")
        elif not any(p.fullmatch(s) for p in pats):
            out.append(s)
    return out


def cmd_start(a, method=None):
    review_dir = Path(a.review_dir)
    review_dir.mkdir(parents=True, exist_ok=True)
    n = a.round
    ps = paths(review_dir, n)
    if ps["record"].exists() and not a.force:
        die(f"{ps['record']} はもうある（その巡はやり直さない。次の巡は --round {n + 1}。書き直すなら --force）")
    if not ps["request"].exists():
        die(f"依頼文 {ps['request']} が無い（references/review.md の雛形で先に書く）")
    if ps["result"].exists():
        die(f"{ps['result']} が起動の前からある（前の結果を消すか、次の巡の番号にする）")
    case = case_dir(review_dir)
    inputs, hashes = {}, {}
    for key, name in INPUT_NAMES.items():
        override = getattr(a, key, None)
        f = Path(override) if override else case / name
        if not f.is_absolute():
            f = (Path.cwd() / f).resolve()
        if not f.exists():
            die(f"検品に渡す file が無い: {f}")
        inputs[key] = os.path.relpath(f, case)
        hashes[key] = sha256(f)
    extra_in, extra_hash = {}, {}
    for e in getattr(a, "extra", None) or []:
        f = Path(e)
        if not f.is_absolute():
            f = (Path.cwd() / f).resolve()
        if not f.exists():
            die(f"検品に渡す file が無い: {f}")
        extra_in[f.name] = os.path.relpath(f, case)
        extra_hash[f.name] = sha256(f)
    extra = request_deviations(ps["request"], {INPUT_NAMES[k]: Path(v).name for k, v in inputs.items()})
    if extra:
        die(f"依頼文 {ps['request']} に、雛形（references/review.md §reviewer への依頼文）に無い行がある。"
            "作り手の観点・説明・目安の時間を reviewer に渡さないため、雛形の <…> を埋めるだけにして書き直す"
            "（当てはまらない行は書き換えずに消す。例: pptx が無い時の check.py pptx の行）:\n  "
            + "\n  ".join(extra))
    rec = {
        "schema": SCHEMA,
        "recorder": RECORDER,
        "round": n,
        "method": method or a.method,
        "status": "started",
        "started_at": now(),
        "ended_at": None,
        "host": platform.node(),
        # Codex の囲いの中で動く command には CODEX_SANDBOX などが入る（値は記録しない。有無だけ）
        "codex_env": any(k in os.environ for k in CODEX_ENV_KEYS),
        "inputs": inputs,
        "inputs_sha256": hashes,
        **({"extra_inputs": extra_in, "extra_inputs_sha256": extra_hash} if extra_in else {}),
        "request_file": ps["request"].name,
        "request_sha256": sha256(ps["request"]),
        "reviewer_id": None,
        "exit_status": None,
        "result_file": ps["result"].name,
    }
    save(review_dir, n, rec)
    return rec


def _finish_result(review_dir, n, rec):
    ps = paths(review_dir, n)
    if not ps["result"].exists():
        rec["status"] = "no-result"
        save(review_dir, n, rec)
        die(f"検品の結果 {ps['result']} が無い（reviewer が書いていない。1 回だけ起動し直す。だめなら未検品）")
    st = ps["result"].stat()
    rec["result_sha256"] = sha256(ps["result"])
    rec["result_mtime"] = datetime.datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")


def cmd_finish(a):
    rec = load(a.review_dir, a.round)
    if rec.get("status") != "started":
        die(f"この巡の記録は status={rec.get('status')}（finish は start の後に 1 回だけ）")
    if rec["method"] == "fresh-process":
        die("別プロセスの検品は run で記録する（pid・終了コード・出力を script が取るため）")
    if not a.reviewer_id.strip():
        die("--reviewer-id が空（subagent の起動で返ってきた id を書く）")
    rec["ended_at"] = now()
    rec["reviewer_id"] = a.reviewer_id.strip()
    if a.exit is not None:
        rec["exit_status"] = a.exit
    else:
        rec["exit_status"] = None
        rec["exit_note"] = "subagent は終了コードを返さない。返事が返り、結果の file がある = 正常終了として扱う"
    if a.transcript:
        t = Path(a.transcript)
        if not t.exists():
            die(f"--transcript の file が無い: {t}")
        rec["transcript"] = str(t.resolve())
        rec["transcript_sha256"] = sha256(t)
    _finish_result(a.review_dir, a.round, rec)
    rec["status"] = "finished"
    save(a.review_dir, a.round, rec)
    print(f"記録しました: {paths(a.review_dir, a.round)['record']}")
    return 0


def _session_id(run_file):
    """実行記録の先頭から、別プロセスの会話 id（codex: thread.started の thread_id / claude: session_id）を探す。"""
    try:
        with open(run_file, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i > 200:
                    break
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                for k in ("thread_id", "session_id"):
                    if isinstance(obj, dict) and obj.get(k):
                        return str(obj[k])
    except OSError:
        pass
    m = re.search(r'"(?:thread_id|session_id)"\s*:\s*"([^"]+)"', Path(run_file).read_text(encoding="utf-8", errors="replace")[:200000])
    return m.group(1) if m else None


def cmd_run(a):
    cmd = a.cmd
    if not cmd:
        die("起動する command を -- の後に書く")
    rec = cmd_start(a, method="fresh-process")
    ps = paths(a.review_dir, a.round)
    stdin = open(a.stdin, "rb") if a.stdin else subprocess.DEVNULL
    rec["command"] = cmd
    rec["stdin_file"] = a.stdin and os.path.relpath(Path(a.stdin).resolve(), case_dir(a.review_dir))
    try:
        with open(ps["run"], "wb") as out, open(ps["stderr"], "wb") as err:
            try:
                proc = subprocess.Popen(cmd, stdin=stdin, stdout=out, stderr=err, cwd=a.cwd or None)
            except OSError as e:
                rec["status"] = "launch-failed"
                rec["ended_at"] = now()
                rec["error"] = str(e)
                save(a.review_dir, a.round, rec)
                die(f"起動できない: {e}")
            rec["pid"] = proc.pid
            save(a.review_dir, a.round, rec)
            code = proc.wait()
    finally:
        if a.stdin:
            stdin.close()
    rec["ended_at"] = now()
    rec["exit_status"] = code
    rec["run_file"] = ps["run"].name
    rec["run_sha256"] = sha256(ps["run"])
    rec["run_bytes"] = ps["run"].stat().st_size
    sid = _session_id(ps["run"])
    rec["reviewer_id"] = sid or f"pid:{proc.pid}"
    if sid:
        rec["session_id"] = sid
    if code != 0:
        rec["status"] = "failed"
        save(a.review_dir, a.round, rec)
        die(f"reviewer のプロセスが終了コード {code} で終わった（{ps['stderr']} を読む。1 回だけ起動し直す。だめなら未検品）")
    _finish_result(a.review_dir, a.round, rec)
    rec["status"] = "finished"
    save(a.review_dir, a.round, rec)
    print(f"記録しました: {ps['record']}（pid {proc.pid}・終了コード {code}・reviewer {rec['reviewer_id']}）")
    return 0


def cmd_show(a):
    print(json.dumps(load(a.review_dir, a.round), ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="sub", required=True)

    def common(p):
        p.add_argument("review_dir", help="案件フォルダの review/")
        p.add_argument("--round", type=int, required=True, help="何巡目か（1, 2, …）")

    def inputs(p):
        p.add_argument("--brief", help="BRIEF の path（既定: 案件フォルダの BRIEF.md）")
        p.add_argument("--ledger", help="出典台帳の path（既定: 案件フォルダの ledger.md）")
        p.add_argument("--deck", help="スライドの path（既定: 案件フォルダの deck.html）")
        p.add_argument("--extra", action="append", default=[],
                       help="一緒に検品する配布物の HTML など（何度でも。check.py manifest が配布物の照合に使う）")
        p.add_argument("--force", action="store_true", help="同じ巡の記録を書き直す")

    p = sub.add_parser("start", help="subagent を起動する直前に")
    common(p)
    inputs(p)
    p.add_argument("--method", choices=["subagent"], default="subagent")
    p.set_defaults(fn=cmd_start)
    p = sub.add_parser("finish", help="subagent の返事が返った直後に")
    common(p)
    p.add_argument("--reviewer-id", required=True)
    p.add_argument("--exit", type=int)
    p.add_argument("--transcript", help="subagent の実行記録の file（あれば sha256 を残す）")
    p.set_defaults(fn=cmd_finish)
    p = sub.add_parser("run", help="別プロセスの reviewer を起動して記録する")
    common(p)
    inputs(p)
    p.add_argument("--stdin", help="標準入力に渡す file（依頼文 review/request-<n>.md）")
    p.add_argument("--cwd", help="起動する場所（既定: 今の場所）")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("show")
    common(p)
    p.set_defaults(fn=cmd_show)
    argv = sys.argv[1:]
    cmd = []
    if "--" in argv:
        k = argv.index("--")
        argv, cmd = argv[:k], argv[k + 1:]
    a = ap.parse_args(argv)
    a.cmd = cmd
    if a.sub == "start":
        cmd_start(a)
        print(f"記録を始めました: {paths(a.review_dir, a.round)['record']}（返事が返ったら finish）")
        return 0
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
