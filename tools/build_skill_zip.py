#!/usr/bin/env python3
"""エージェント版 skill (skill/shiryo-kit/) を、Claude・ChatGPT のアプリにアップロードする zip にする (直す人向け)。

  python3 tools/build_skill_zip.py --out DIR   # DIR/shiryo-kit-skill.zip を作る (DIR は repo の外か、git が無視する場所)
  python3 tools/build_skill_zip.py --check     # zip の中身を組み立てて確かめるだけ (何も書かない)。問題があれば NG と exit 1

zip の形 (Claude のヘルプ「カスタムスキルの作成方法」に合わせる):
  shiryo-kit-skill.zip
  └── shiryo-kit/        フォルダ名 = スキルの name。zip の最上位はこのフォルダ (中身を直接置かない)
      ├── SKILL.md       frontmatter だけ、アップロード向けに差し替える (下の UPLOAD_DESCRIPTION)。本文は正本のまま
      ├── references/ scripts/ assets/ agents/
入れない物: __pycache__/、*.pyc、.DS_Store、tests/、out/、.shiryo-preview.json、名前が . で始まる file。

frontmatter を差し替える理由: claude.ai のアップロードは description を 200 字まで、項目は name と description
(と dependencies) としている。正本の SKILL.md (Claude Code・Codex 用) は description が長く、license・compatibility も持つ。
正本は変えず、zip の中の SKILL.md だけを差し替える。
"""
import argparse, io, re, subprocess, sys, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / 'skill' / 'shiryo-kit'
NAME = 'shiryo-kit'
ZIP_NAME = 'shiryo-kit-skill.zip'
UPLOAD_DESCRIPTION = ('「資料作って」「スライド作って」「セミナー資料」「顧問先向けの説明資料」「提案資料」「報告資料」「読み原稿」を頼まれた時に使う。'
                      '士業・中小企業の日本語の資料を、聴き取り・原典での確認 (確かめられない所は [要確認])・別の目での検品を経て、'
                      '編集できる pptx・PDF・読み原稿にする。')
SKIP_DIRS = {'__pycache__', 'tests', 'out'}
SKIP_FILES = {'.DS_Store', '.shiryo-preview.json'}


def source_files():
    for p in sorted(SRC.rglob('*')):
        rel = p.relative_to(SRC)
        if not p.is_file() or any(part in SKIP_DIRS or part.startswith('.') for part in rel.parts[:-1]):
            continue
        if p.name in SKIP_FILES or p.name.startswith('.') or p.suffix == '.pyc':
            continue
        yield rel, p


def upload_skill_md():
    text = (SRC / 'SKILL.md').read_text(encoding='utf-8')
    m = re.match(r'---\n.*?\n---\n', text, re.S)
    assert m, 'SKILL.md の先頭に frontmatter (--- で囲んだ部分) が無い'
    assert re.search(r'^name: ' + re.escape(NAME) + r'$', m.group(0), re.M), f'正本の name が {NAME} でない'
    return f'---\nname: {NAME}\ndescription: {UPLOAD_DESCRIPTION}\n---\n' + text[m.end():]


def build_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel, p in source_files():
            arc = f'{NAME}/{rel.as_posix()}'
            if rel.as_posix() == 'SKILL.md':
                z.writestr(arc, upload_skill_md())
            else:
                z.write(p, arc)
    return buf.getvalue()


def problems(data):
    bad = []
    if len(UPLOAD_DESCRIPTION) > 200:
        bad.append(f'description が {len(UPLOAD_DESCRIPTION)} 字 (200 字まで)')
    if ': ' in UPLOAD_DESCRIPTION or '<' in UPLOAD_DESCRIPTION or '>' in UPLOAD_DESCRIPTION:
        bad.append('description に「: 」や < > を入れない (YAML とアップロードが壊れる)')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        roots = {n.split('/', 1)[0] for n in names}
        if roots != {NAME}:
            bad.append(f'zip の最上位が {sorted(roots)} (shiryo-kit フォルダ 1 つだけであること)')
        if f'{NAME}/SKILL.md' not in names:
            bad.append('shiryo-kit/SKILL.md が無い')
        else:
            md = z.read(f'{NAME}/SKILL.md').decode('utf-8')
            fm = md.split('---\n')[1]
            keys = [l.split(':', 1)[0] for l in fm.splitlines() if l and not l.startswith(' ')]
            if keys != ['name', 'description']:
                bad.append(f'zip の SKILL.md の frontmatter が {keys} (name と description だけにする)')
            for ref in sorted(set(re.findall(r'`((?:references|scripts|assets|agents)/[^`*\s]+?)`', md))):
                ref = ref.rstrip('/')
                if '...' in ref or '<' in ref:
                    continue
                if not any(n == f'{NAME}/{ref}' or n.startswith(f'{NAME}/{ref}/') for n in names):
                    bad.append(f'SKILL.md が指す {ref} が zip に無い')
        for n in names:
            parts = n.split('/')
            if any(x in SKIP_DIRS or x in SKIP_FILES or x.endswith('.pyc') for x in parts):
                bad.append(f'入れない物が入っている: {n}')
    return bad, len(names)


def inside_repo_and_tracked(out_dir):
    try:
        out_dir.relative_to(REPO)
    except ValueError:
        return False
    r = subprocess.run(['git', '-C', str(REPO), 'check-ignore', '-q', str(out_dir / ZIP_NAME)])
    return r.returncode != 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--out', metavar='DIR', help=f'DIR/{ZIP_NAME} を作る')
    g.add_argument('--check', action='store_true', help='組み立てて確かめるだけ')
    a = ap.parse_args()
    data = build_bytes()
    bad, count = problems(data)
    for b in bad:
        print(f'NG {b}')
    if bad:
        sys.exit(1)
    if a.check:
        print(f'OK {ZIP_NAME} の中身 ({count} files、最上位 {NAME}/、description {len(UPLOAD_DESCRIPTION)} 字)')
        return
    out_dir = Path(a.out).resolve()
    if inside_repo_and_tracked(out_dir):
        sys.exit(f'NG {out_dir} は repo の中で git が無視しない場所です。repo の外か、.gitignore にある場所 (例 dist/) を指定してください')
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / ZIP_NAME
    out.write_bytes(data)
    print(f'zip {out} ({count} files、{len(data) // 1024} KB。正本 skill/shiryo-kit/ は変えていない)')


if __name__ == '__main__':
    main()
