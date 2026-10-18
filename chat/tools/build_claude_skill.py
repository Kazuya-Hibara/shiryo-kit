#!/usr/bin/env python3
"""claude.ai 用 skill フォルダ (chat/claude-ai-skill/shiryo-kit-chat/) を、正本から作り直す。

正本: chat/instructions.md (指示文) と chat/knowledge/*.md (参考資料)。
skill フォルダの SKILL.md と references/ は生成物なので、直接直さずにこの script を流す。

  python3 chat/tools/build_claude_skill.py            # skill フォルダを作り直す
  python3 chat/tools/build_claude_skill.py --check    # ずれが無ければ OK を出す。ずれていれば DRIFT を出して exit 1
  python3 chat/tools/build_claude_skill.py --zip DIR  # 正本から DIR/shiryo-kit-chat.zip だけを作る (zip の最上位 = フォルダ。repo の中は書き換えない)
"""
import argparse, sys, zipfile
from pathlib import Path

CHAT = Path(__file__).resolve().parent.parent
NAME = 'shiryo-kit-chat'
SKILL_DIR = CHAT / 'claude-ai-skill' / NAME
# claude.ai の upload は仕様外の frontmatter を拒む。support 記事は description を 200 字までとしているので、それに収める。
DESCRIPTION = ('使う時は「資料作って」「スライド作って」「セミナー資料」「顧問先向けの説明資料」「提案資料」「読み原稿」を頼まれた時。'
               '士業・中小企業の日本語の資料の中身を、作る前に聴き切ってから、骨子・スライド文面・読み原稿・出典一覧 (確かめられない所は [要確認])・メモカードの順に出す。')

HEAD = f"""---
name: {NAME}
description: {DESCRIPTION}
---

# shiryo-kit チャット版 (claude.ai 用 skill)

この skill は、資料・スライド・セミナー資料・説明資料・提案資料・読み原稿を頼まれた時に使う。以下の決まりと進め方に、最初から最後まで従う。
参考資料は `references/` にある: `references/hearing-guide.md` (ヒアリング)、`references/evidence-rules.md` (出典の確かめ方)、`references/doctrine.md` (資料の判断の軸)。迷った時に読む。この SKILL.md と食い違ったら SKILL.md を優先する。
この skill では script を動かさない。成果物は会話の中の文章として出す。

"""

TAIL = """
## Claude Slides と組み合わせる

スライド文面・読み原稿・出典一覧を出し終えた後、本人が「スライドにして」と頼んだ時だけ、Claude Slides (claude.ai のスライド機能) でデッキを作ってよい。
- 作る前に一言伝える: 「スライドは claude.ai (Anthropic のサーバー) に保存され、サイドバーの Artifacts に残ります。顧問先の個人情報は入っていません。作ってよいですか」。本人が了承してから作る。
- 中身は、承認済みのスライド文面をそのまま使う。タイトル・本文・数字・出典の表示・[要確認] を変えない、足さない、消さない。読み原稿は各スライドのノート欄に入れられれば入れる。
- 描画の都合で文言を縮めたくなったら、勝手に縮めず、どの枚のどの文をどう縮めるかを示して本人に聞く。
- 作った後、スライドの文言と承認済みの文面を照らし、違いがあれば一覧で伝える。これも「検品」ではない。最後に「未検品」の表示と本人用の確認リストを改めて添える。
- PowerPoint (.pptx) に書き出した時、文字が編集できるか・日本語の書体が崩れないかは確かめられていない。本人に PowerPoint で開いて確かめてもらう。
"""

def instructions_body():
    t = (CHAT / 'instructions.md').read_text(encoding='utf-8')
    lines = t.splitlines()
    assert lines[0].startswith('# '), 'instructions.md の 1 行目は題であること'
    body = '\n'.join(lines[1:]).strip() + '\n'
    old = [l for l in body.splitlines() if l.startswith('- 参考資料 (ヒアリングの手引き')]
    assert len(old) == 1, 'instructions.md の「参考資料」の行が見つからない'
    return body.replace(old[0], '- 迷った時は `references/` の参考資料を読む (この SKILL.md の冒頭を参照)。')

def expected():
    files = {'SKILL.md': HEAD + instructions_body() + TAIL}
    for p in sorted((CHAT / 'knowledge').glob('*.md')):
        files[f'references/{p.name}'] = p.read_text(encoding='utf-8')
    return files

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--zip', metavar='DIR')
    a = ap.parse_args()
    assert len(DESCRIPTION) <= 200, f'description が {len(DESCRIPTION)} 字 (200 字まで)'
    assert ': ' not in DESCRIPTION and '<' not in DESCRIPTION, 'description に「: 」や < を入れない (YAML とアップロードが壊れる)'
    files = expected()
    if a.check:
        actual = {str(p.relative_to(SKILL_DIR)): p.read_text(encoding='utf-8')
                  for p in SKILL_DIR.rglob('*') if p.is_file()}
        bad = sorted(set(files) ^ set(actual)) + sorted(k for k in files if k in actual and files[k] != actual[k])
        for k in bad:
            print(f'DRIFT {k}')
        if bad:
            sys.exit(1)
        print(f'OK {SKILL_DIR.relative_to(CHAT.parent)} は正本と一致 ({len(files)} files)')
        return
    if a.zip:
        out = Path(a.zip) / f'{NAME}.zip'
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for rel, text in files.items():
                z.writestr(f'{NAME}/{rel}', text)
        print(f'zip {out} ({len(files)} files、正本から作成。repo の写しは変えていない)')
        return
    for rel, text in files.items():
        dst = SKILL_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding='utf-8')
    for p in SKILL_DIR.rglob('*'):
        if p.is_file() and str(p.relative_to(SKILL_DIR)) not in files:
            p.unlink()
    print(f'built {SKILL_DIR.relative_to(CHAT.parent)} ({len(files)} files, SKILL.md {files["SKILL.md"].count(chr(10))} lines)')

if __name__ == '__main__':
    main()
