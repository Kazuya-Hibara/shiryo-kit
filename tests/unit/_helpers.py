"""tests/unit の共通部品: scripts の場所・CLI の実行・依存の有無。"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skill" / "shiryo-kit" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
TRAPS = ROOT / "tests" / "fixtures" / "review-traps"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

HAS_PPTX = importlib.util.find_spec("pptx") is not None and importlib.util.find_spec("lxml") is not None


def _has_chrome():
    node = shutil.which("node")
    if not node:
        return False
    r = subprocess.run([node, str(SCRIPTS / "find_chrome.mjs")], capture_output=True, text=True)
    return r.returncode == 0 and bool(r.stdout.strip())


HAS_CHROME = _has_chrome()


CODEX_ENV_KEYS = ("CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED", "CODEX_THREAD_ID")


def run(script, *args, cwd=None, timeout=600, env=None):
    """scripts/<script> を別プロセスで実行して (終了コード, stdout, stderr)。
    Codex の中で試験を回しても結果が変わらないよう、Codex の印の環境変数は外す (env で足せる)。"""
    base = {k: v for k, v in os.environ.items() if k not in CODEX_ENV_KEYS}
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True,
                       encoding="utf-8", cwd=cwd, timeout=timeout, env={**base, "PYTHONIOENCODING": "utf-8", **(env or {})})
    return r.returncode, r.stdout, r.stderr


def check(*args, **kw):
    return run("check.py", *args, **kw)


def fails(out):
    return [ln for ln in out.splitlines() if ln.startswith("FAIL")]


def warns(out):
    return [ln for ln in out.splitlines() if ln.startswith("WARN")]


def deck_html(*slides, title="試験用デッキ", css=True):
    """部品集の CSS を使わない最小のデッキ（16:9 の宣言だけ入れる）。slides は section の中身。"""
    style = ("<style>.s{width:338.67mm;height:190.5mm;position:relative;overflow:hidden;padding:12mm;box-sizing:border-box}"
             "h1{font-size:26pt;margin:0 0 6mm}p,li{font-size:18pt}aside.notes{display:none}"
             "@page{size:338.67mm 190.5mm;margin:0}</style>") if css else ""
    body = "\n".join(s if s.lstrip().startswith("<section") else f'<section class="s">{s}</section>' for s in slides)
    return f'<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>{title}</title>{style}</head><body>\n{body}\n</body></html>'


class TempDir:
    def __enter__(self):
        self._td = tempfile.TemporaryDirectory()
        return Path(self._td.name)

    def __exit__(self, *exc):
        self._td.cleanup()


APPROVED_BRIEF = """---
spec_rev: 1
status: 承認済み
案件: 試験用
---

# BRIEF — 試験用

## 要約の提示
- 2026-10-19 09:00 要約 rev 1 を見せた

## 承認記録
- 2026-10-19 09:05 本人「この内容で。」 (要約 rev 1 への返事。spec_rev 1) ※試験用に作った記録
"""


def write_approved_brief(folder):
    """関門 1 を通る最小の BRIEF.md（書き出し・部品からの作成を試す試験用）。"""
    (Path(folder) / "BRIEF.md").write_text(APPROVED_BRIEF, encoding="utf-8")
