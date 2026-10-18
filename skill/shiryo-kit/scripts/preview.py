#!/usr/bin/env python3
"""shiryo-kit: 案件フォルダをこのパソコンの中だけで見られるようにする小さな表示用サーバー（標準ライブラリだけ）。

使い方:
  python3 preview.py 案件フォルダ              # 裏で起動して URL と PID を表示し、すぐ戻る（既定）
  python3 preview.py 案件フォルダ --stop       # 止める
  python3 preview.py 案件フォルダ --port 9000  # 待ち受けの番号（使われていれば次の空き番号）
  python3 preview.py 案件フォルダ --foreground # この画面で動かし続ける（Ctrl+C で止める）

Codex（ChatGPT デスクトップ）の Annotate や Claude Desktop のブラウザ欄で、表示された URL を開いて
スライドを指しながら直しを頼むために使う。127.0.0.1（このパソコン）だけで待ち受け、外からはつながらない。
動いている間は 案件フォルダ/.shiryo-preview.json に {pid, port, url} を書く（--stop がこれを読む）。
同じフォルダでもう動いていれば、新しく起動せずにその URL を表示する。
"""
import argparse
import datetime
import functools
import http.server
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PIDFILE = ".shiryo-preview.json"
PING = "/__shiryo_preview__"


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # 直した HTML がすぐ見えるように
        super().end_headers()

    def do_GET(self):
        if self.path == PING:
            body = str(os.getpid()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if Path(urllib.parse.urlparse(self.path).path).name == PIDFILE:
            self.send_error(404)
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        pass


def free_port(start):
    for p in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    sys.exit(f"使えるポートが見つかりません（{start}〜{start + 49}）。--port で別の番号を指定してください。")


def read_pidfile(root):
    p = root / PIDFILE
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None


def ping(info, timeout=2.0):
    """記録の URL に問い合わせ、答えた pid を返す（動いていなければ None）。pid の使い回しで別のプロセスを止めないため。"""
    try:
        with urllib.request.urlopen(info["url"].rstrip("/") + PING, timeout=timeout) as r:
            return int(r.read().decode().strip())
    except (OSError, ValueError, KeyError):
        return None


def print_urls(root, base):
    for f in sorted(root.glob("*.html")):
        print(f"  {base}{urllib.parse.quote(f.name)}")


def serve(root, port):
    handler = functools.partial(Handler, directory=str(root))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    base = f"http://127.0.0.1:{port}/"
    info = {"pid": os.getpid(), "port": port, "url": base, "dir": str(root),
            "started_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    (root / PIDFILE).write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")

    def stop(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    return httpd, base


def cleanup(root):
    info = read_pidfile(root)
    if info and info.get("pid") == os.getpid():
        (root / PIDFILE).unlink(missing_ok=True)


def run_foreground(root, port, quiet=False):
    httpd, base = serve(root, free_port(port))
    if not quiet:
        print(f"表示中: {base}  （PID {os.getpid()}。止める時は Ctrl+C）")
        print_urls(root, base)
        sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        cleanup(root)


def start_background(root, port):
    info = read_pidfile(root)
    if info and ping(info) == info.get("pid"):
        print(f"もう表示中です: {info['url']}  （PID {info['pid']}。止める: python3 {Path(__file__).name} {root} --stop）")
        print_urls(root, info["url"])
        return 0
    (root / PIDFILE).unlink(missing_ok=True)
    cmd = [sys.executable, str(Path(__file__).resolve()), str(root), "--port", str(port), "--foreground", "--quiet"]
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "close_fds": True}
    if os.name == "nt":
        kw["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kw)
    deadline = time.time() + 15
    while time.time() < deadline:
        info = read_pidfile(root)
        if info and info.get("pid") == proc.pid and ping(info, 1.0) == proc.pid:
            print(f"表示中: {info['url']}  （PID {proc.pid}。止める: python3 {Path(__file__).name} {root} --stop）")
            print_urls(root, info["url"])
            return 0
        if proc.poll() is not None:
            break
        time.sleep(0.2)
    sys.exit("表示用のサーバーが起動しませんでした。--foreground を付けて実行し、出たエラーを読んでください。")


def stop_server(root):
    info = read_pidfile(root)
    if not info:
        print(f"表示用のサーバーは動いていません（{root / PIDFILE} が無い）")
        return 0
    pid = info.get("pid")
    if ping(info) != pid:
        (root / PIDFILE).unlink(missing_ok=True)
        print(f"表示用のサーバーは動いていません（記録だけ残っていたので消しました。PID {pid}）")
        return 0
    os.kill(pid, signal.SIGTERM)
    for _ in range(50):
        if ping(info, 0.5) != pid:
            break
        time.sleep(0.1)
    else:
        sys.exit(f"止まりませんでした（PID {pid}）。このパソコンのタスクの一覧から python を終了してください。")
    (root / PIDFILE).unlink(missing_ok=True)
    print(f"止めました: {info.get('url')}（PID {pid}）")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", help="表示するフォルダ（HTML デッキのある案件フォルダ）")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--stop", action="store_true", help="動いている表示用サーバーを止める")
    ap.add_argument("--foreground", action="store_true", help="裏に回さず、この画面で動かす（Ctrl+C で止める）")
    ap.add_argument("--background", action="store_true", help="裏で動かす（既定と同じ）")
    ap.add_argument("--quiet", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    root = Path(a.dir).resolve()
    if not root.is_dir():
        sys.exit(f"フォルダが見つかりません: {root}")
    if a.stop:
        return stop_server(root)
    if a.foreground:
        run_foreground(root, a.port, a.quiet)
        return 0
    return start_background(root, a.port)


if __name__ == "__main__":
    sys.exit(main())
