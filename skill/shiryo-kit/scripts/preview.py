#!/usr/bin/env python3
"""shiryo-kit: 案件フォルダをこのパソコンの中だけで見られるようにする小さな表示用サーバー（標準ライブラリだけ）。

使い方:
  python3 preview.py 案件フォルダ              # http://127.0.0.1:8765/ で表示。止める時は Ctrl+C
  python3 preview.py 案件フォルダ --port 9000

Codex（ChatGPT デスクトップ）の Annotate や Claude Desktop のブラウザ欄で、表示された URL を開いて
スライドを指しながら直しを頼むために使う。127.0.0.1（このパソコン）だけで待ち受け、外からはつながらない。
"""
import argparse
import functools
import http.server
import socket
import sys
import urllib.parse
from pathlib import Path


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # 直した HTML がすぐ見えるように
        super().end_headers()

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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", help="表示するフォルダ（HTML デッキのある案件フォルダ）")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    root = Path(a.dir).resolve()
    if not root.is_dir():
        sys.exit(f"フォルダが見つかりません: {root}")
    port = free_port(a.port)
    handler = functools.partial(Handler, directory=str(root))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    base = f"http://127.0.0.1:{port}/"
    print(f"表示中: {base}  （止める時は Ctrl+C）")
    for f in sorted(root.glob("*.html")):
        print(f"  {base}{urllib.parse.quote(f.name)}")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
