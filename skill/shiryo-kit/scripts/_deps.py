"""shiryo-kit: 依存の確認。足りない時は、何を入れればよいかを日本語で表示して止める。"""
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NODE_MIN = 22


class BrowserUnavailable(SystemExit):
    """Node・Chrome が無い・起動しない（描画の失敗とは分ける）。build.py の予備の書き出しと check.py pptx の静的な比較は、これの時だけ切り替える。"""


def _pip_hint():
    if platform.system() == "Windows":
        return "py -m pip install python-pptx lxml"
    return ("python3 -m venv ~/.shiryo-kit-venv && ~/.shiryo-kit-venv/bin/pip install python-pptx lxml\n"
            "  （以後は ~/.shiryo-kit-venv/bin/python3 で scripts を実行する。"
            "venv を使わないなら: python3 -m pip install --user python-pptx lxml）")


def require_python_libs():
    missing = []
    for mod, pkg in (("pptx", "python-pptx"), ("lxml", "lxml")):
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        sys.exit(f"Python の部品が足りません: {', '.join(missing)}\n入れ方:\n  {_pip_hint()}\n"
                 f"（今の Python: {sys.executable}）")


def node_hint():
    s = platform.system()
    if s == "Darwin":
        return "brew install node（Homebrew が無ければ https://nodejs.org/ から LTS 版のインストーラーを入れる）"
    if s == "Windows":
        return "winget install OpenJS.NodeJS.LTS（または https://nodejs.org/ から LTS 版を入れる）。入れた後はターミナルを開き直す"
    return "https://nodejs.org/ の手順か、ディストリビューションのパッケージで Node.js 22 以上を入れる"


def require_node():
    """Node 22+ のパスを返す。無い・古い時は対処を表示して止める。"""
    node = shutil.which("node")
    if not node:
        raise BrowserUnavailable(f"Node.js が見つかりません（スライドの描画に Node.js {NODE_MIN} 以上が要ります）。\n入れ方: {node_hint()}")
    try:
        v = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        v = ""
    m = re.match(r"v(\d+)", v)
    if not m or int(m.group(1)) < NODE_MIN:
        raise BrowserUnavailable(f"Node.js が古いか確認できません（{v or '不明'}）。{NODE_MIN} 以上が要ります。\n入れ方: {node_hint()}")
    return node


def find_chrome():
    """(path, None) か (None, エラー文)。"""
    node = require_node()
    r = subprocess.run([node, str(HERE / "find_chrome.mjs")], capture_output=True, text=True, encoding="utf-8", timeout=60)
    if r.returncode == 0:
        return r.stdout.strip(), None
    return None, r.stderr.strip()
