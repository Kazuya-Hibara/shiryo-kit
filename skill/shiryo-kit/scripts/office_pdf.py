"""shiryo-kit: LibreOffice で pptx を PDF にする（Chrome が使えない時の予備の書き出しで使う）。

囲い（sandbox）の中では、素の soffice が止まったまま戻らないことがある。そこで:
  - 毎回まっさらな利用者プロファイル（一時フォルダ）を使う（既定のプロファイルを作れない環境で止まらないように）
  - 画面の無い描画部品を使う（Linux では SAL_USE_VCLPLUGIN=svp）
  - 時間の上限（既定 180 秒、SHIRYO_SOFFICE_TIMEOUT）を過ぎたら、soffice ごと止めて「作れなかった」と返す
作れなかった時は理由を返し、PDF は作らない（作ったふりをしない）。
"""
import os
import platform
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path

CANDIDATES = (
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


def find_soffice():
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for c in CANDIDATES:
        if Path(c).exists():
            return c
    return None


def pptx_to_pdf(pptx, out_pdf, timeout=None):
    """(True, None) か (False, 理由)。"""
    soffice = find_soffice()
    if not soffice:
        return False, "LibreOffice（soffice）が見つからない"
    if not timeout:
        try:
            timeout = int(os.environ.get("SHIRYO_SOFFICE_TIMEOUT", "180"))
        except ValueError:
            timeout = 180
    env = dict(os.environ)
    if platform.system() == "Linux":
        env["SAL_USE_VCLPLUGIN"] = "svp"
    with tempfile.TemporaryDirectory(prefix="shiryo_lo_") as td:
        profile = Path(td) / "profile"
        outdir = Path(td) / "out"
        outdir.mkdir()
        cmd = [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--norestore", "--nologo",
               "--nodefault", "--nolockcheck", "--convert-to", "pdf", "--outdir", str(outdir), str(Path(pptx).resolve())]
        kw = {"start_new_session": True} if os.name != "nt" else {}
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **kw)
        except OSError as e:
            return False, f"LibreOffice を起動できない（{e}）"
        try:
            _, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                if os.name != "nt":
                    os.killpg(p.pid, signal.SIGKILL)
                else:  # soffice.exe の子の soffice.bin ごと止める（親だけ止めると子が出力の管を握ったまま残る）
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, timeout=30)
            except (OSError, subprocess.SubprocessError):
                pass
            try:
                p.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                p.kill()
            return False, f"LibreOffice が {timeout} 秒で終わらなかった（止めた）"
        made = outdir / (Path(pptx).stem + ".pdf")
        if p.returncode != 0 or not made.exists() or made.stat().st_size == 0:
            tail = (err or b"").decode("utf-8", "replace").strip()[-300:]
            return False, f"LibreOffice の変換が失敗した（終了コード {p.returncode}{'、' + tail if tail else ''}）"
        shutil.move(str(made), str(out_pdf))
    return True, None
