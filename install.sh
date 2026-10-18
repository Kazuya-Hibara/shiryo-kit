#!/usr/bin/env bash
# shiryo-kit を Claude Code / Codex の skill フォルダに入れる (macOS / Linux)。
#
#   ./install.sh            Claude Code と Codex の両方に入れる (コピー)
#   ./install.sh --claude   Claude Code だけ   (~/.claude/skills/shiryo-kit)
#   ./install.sh --codex    Codex だけ         (~/.agents/skills/shiryo-kit)
#   ./install.sh --link     コピーの代わりにリンクを張る (このフォルダを更新すると skill も変わる)
#
# 何度実行しても同じ結果になる。shiryo-kit 以外のフォルダには触らない。
# 同じ名前で中身が shiryo-kit でないフォルダがあれば、上書きせずに止める。
set -eu

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
}

want_claude=0
want_codex=0
mode=copy
for arg in "$@"; do
  case "$arg" in
    --claude) want_claude=1 ;;
    --codex)  want_codex=1 ;;
    --link)   mode=link ;;
    --copy)   mode=copy ;;
    -h|--help) usage; exit 0 ;;
    *) echo "知らない指定です: $arg" >&2; usage >&2; exit 2 ;;
  esac
done
if [ "$want_claude" -eq 0 ] && [ "$want_codex" -eq 0 ]; then
  want_claude=1
  want_codex=1
fi

here=$(cd "$(dirname "$0")" && pwd -P)
src="$here/skill/shiryo-kit"

# SKILL.md の frontmatter に name: shiryo-kit があるフォルダだけを shiryo-kit と認める
is_shiryo_dir() {
  [ -f "$1/SKILL.md" ] || return 1
  awk 'NR==1 { if ($0 != "---") exit; next } $0 == "---" { exit } { print }' "$1/SKILL.md" |
    grep -Eq '^name:[[:space:]]*shiryo-kit[[:space:]]*$'
}

if ! is_shiryo_dir "$src"; then
  echo "skill のフォルダが見つかりません: $src" >&2
  echo "このスクリプトは shiryo-kit のフォルダの一番上 (install.sh がある所) に置いたまま実行してください。" >&2
  exit 1
fi

same_tree() {
  diff -rq -x __pycache__ -x '*.pyc' -x .DS_Store "$1" "$2" >/dev/null 2>&1
}

copy_into() {  # $1 = 置き場所。隣に一時フォルダを作ってから入れ替える
  tmp="$1.shiryo-kit-tmp.$$"
  rm -rf "$tmp"
  cp -R "$src" "$tmp"
  find "$tmp" \( -name __pycache__ -o -name '*.pyc' -o -name .DS_Store \) -prune -exec rm -rf {} +
  rm -rf "$1"
  mv "$tmp" "$1"
}

failed=0
install_one() {  # $1 = 表示名, $2 = 置き場所
  label=$1
  dest=$2
  parent=$(dirname "$dest")

  if [ -L "$dest" ]; then
    if real=$(cd "$dest" 2>/dev/null && pwd -P); then
      if [ "$real" = "$src" ] && [ "$mode" = link ]; then
        echo "[$label] そのまま (もうリンク済み): $dest -> $src"
        return 0
      fi
      if ! is_shiryo_dir "$real"; then
        echo "[$label] 止めました: $dest は shiryo-kit ではないフォルダへのリンクです ($real)。手で確かめてください。" >&2
        failed=1
        return 0
      fi
    fi
    # shiryo-kit へのリンク、または切れたリンク。リンクだけを外す (リンク先の中身は消さない)
    rm "$dest"
    echo "[$label] 前のリンクを外しました: $dest"
  elif [ -e "$dest" ]; then
    if [ ! -d "$dest" ] || ! is_shiryo_dir "$dest"; then
      echo "[$label] 止めました: $dest は shiryo-kit ではありません。上書きしないので、名前を変えるか中身を確かめてください。" >&2
      failed=1
      return 0
    fi
    if [ "$mode" = copy ] && same_tree "$src" "$dest"; then
      echo "[$label] そのまま (最新と同じ): $dest"
      return 0
    fi
  fi

  mkdir -p "$parent"
  if [ "$mode" = link ]; then
    [ -d "$dest" ] && [ ! -L "$dest" ] && rm -rf "$dest" && echo "[$label] 前のコピーを外しました: $dest"
    ln -s "$src" "$dest"
    echo "[$label] リンクを張りました: $dest -> $src"
  else
    existed=0
    [ -d "$dest" ] && existed=1
    copy_into "$dest"
    if [ "$existed" -eq 1 ]; then
      echo "[$label] 新しい版に入れ替えました: $dest"
    else
      echo "[$label] コピーしました: $dest"
    fi
  fi
}

[ "$want_claude" -eq 1 ] && install_one "Claude Code" "$HOME/.claude/skills/shiryo-kit"
[ "$want_codex" -eq 1 ] && install_one "Codex" "$HOME/.agents/skills/shiryo-kit"

if [ "$failed" -ne 0 ]; then
  echo "一部を入れられませんでした (上の「止めました」を見てください)。" >&2
  exit 1
fi
echo "終わりました。Claude Code / Codex を開き直してから「セミナー資料を作りたい」のように頼んでください。"
