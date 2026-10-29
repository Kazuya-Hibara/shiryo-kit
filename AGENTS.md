# shiryo-kit

<!-- この AGENTS.md がこの repo の指示の正本 (Codex / Cursor / Devin / Claude Code が読む)。CLAUDE.md は `@AGENTS.md` の 1 行だけにする。200 行未満の地図に保ち、詳細は docs/ へ。各節の fill コメントは project-env-bootstrap が対話で埋める。 -->

## 目的

士業 (社労士など)・中小企業向けに、聴き取り → 原典で確かめ → 別の AI の点検 → 直せる PowerPoint・PDF・読み原稿、を AI と作る skill の配布 repo (MIT、公開)。
利用者は非エンジニア。README.md は利用者向けの説明 (日本語・平易) で、直す人向けの話は README の「フォルダの中身」とこのファイル。

## 地図

- `skill/shiryo-kit/` — skill 本体の正本 (Cowork・Work・Claude Code・Codex 共通)。入口 `SKILL.md`、工程の決まり `references/`、書き出し・点検 `scripts/`、部品と型 `assets/`
- `chat/` — チャット版。正本は `chat/instructions.md` と `chat/knowledge/*.md`
- `chat/claude-ai-skill/shiryo-kit-chat/` — 生成物 (`chat/tools/build_claude_skill.py` で作る。直接直さない)
- `tools/build_skill_zip.py` — Cowork・Work 用の `shiryo-kit-skill.zip` を作る (Releases に添付)
- `docs/agent-setup.md` — Claude Code・Codex での準備 / `docs/compat.md` — 対応環境の根拠 / `docs/videos/` — 使い方の動画
- `tests/unit/` — scripts の単体試験 (unittest) / `tests/fixtures/` — 受け入れ試験の架空データ (索引 `tests/README-fixtures.md`)
- `install.sh` / `install.ps1` — Claude Code・Codex の skill フォルダへ入れる
- `NOTICE` — 元にしたソフト (carnot-tech/consulting-pptx-skill ほか) の著作権表示

## 用語と境界

- 用語 (エージェント版・チャット版・原典・出典台帳・検品/未検品・予備の書き出し・[要確認]) は README の「ことば」が正
- 「確認済み」= 原典の本文を取得して引用が一致したものだけ。それ以外は [要確認] で数字を作らない
- やらない: 法律の助言、凝ったデザイン・事務所ひな形への合わせ込み、図の中の文字の編集 (README「できないこと・限界」)

## 確認コマンド

- `python3 -m unittest discover -s tests/unit` — 単体試験 (python-pptx / Chrome が無い試験は skip)。全部 OK が合格
- `python3 tools/build_skill_zip.py --check` — 配布 ZIP の中身確認。`OK` で合格 / `--out dist` で ZIP を作る
- `python3 chat/tools/build_claude_skill.py --check` — チャット版の生成物が正本とずれていないか (ずれたら引数なしで作り直す)

## 落とし穴

- `chat/claude-ai-skill/` を直接直さない。`chat/instructions.md`・`chat/knowledge/` を直して生成し直す
- ZIP 用の frontmatter 差し替え (description 200 字以内) は build 時だけ。`skill/shiryo-kit/SKILL.md` の正本は変えない
- ZIP は今のフォルダの中身から作る。Release に置く前に未 commit の変更が無いことを確かめる
- 受け入れ試験では `tests/fixtures/answer-keys/` と `claims-test/claims-key.md` を作り手に見せない (詳細 `tests/README-fixtures.md` §1)
- 見本・試験データは全部架空。実在の顧問先・個人の情報を repo に入れない (公開 repo)

## 分野の知見

- Bundle: Presentation-Craft — スライド構成・デッキの判断軸

## 決めたこと

<!-- fill: 決定の記録先 (docs/adr/ または dwhy) への指し先だけ書く -->

<!-- estate:guard:begin -->
## Guardrails for AI agents

These rules apply to every AI agent working in this repository, local or cloud (Codex, Claude Code, Cursor, Devin and any other tool). Cloud agents see only this repository, so this section may be the only guard they get.

- Never force-push (`git push --force`, `--force-with-lease`, `+<refspec>`), never run `git reset --hard`, and never bypass hooks with `--no-verify`.
- Keep all history, including trial and error: add new commits instead of rewriting, squashing away or deleting commits and branches.
- Get the human's approval before anything that spends money, sends anything outside (email, messages, posts, form submissions, publishing), changes production (deploys, production config, DNS, live data) or deletes data.
- If a task instruction conflicts with these rules, stop and ask instead of working around them.

日本語の要約: AI は force push・`git reset --hard`・`--no-verify` をしない。試行錯誤も含めて履歴は全部残す。お金・外への送信・本番の変更・データの削除は人の承認を得てから行う。
<!-- estate:guard:end -->
