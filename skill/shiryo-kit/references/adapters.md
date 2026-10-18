# adapters.md — 差し替え部品の割当表 (モデル・描画・修正の受け方)

工程 (Port) は変わらない。モデルや道具 (Adapter) は、`ports.md` の契約を満たす限り差し替えてよい。
割当はこの file 1 か所にだけ書く。他の file にモデル名や道具名を書き足さない (例外は、そのまま打つ command の例に付けるモデルの指定。§1 の注記)。

## 1. モデル

| 役 | 何をするか | Claude Code | Codex |
|---|---|---|---|
| 進行役 | P0〜P8 の段取り、ヒアリング、BRIEF、骨子と下書き、出典の取得と照合、修正 | Opus 5.5、effort high (既定) | Astra = Codex のモデル ID `gpt-6-astra`、effort high (`codex exec` なら `-m gpt-6-astra -c model_reasoning_effort="high"`、設定ファイルなら `model = "gpt-6-astra"` と `model_reasoning_effort = "high"`) |
| 読み取り役 (任意) | 過去資料が多い時の抜き出し (要点と口調の引用だけを返す) | subagent。進行役と同じモデルを推奨 | subagent か `codex exec`。同上 |
| 検品役 | P5。作り手と別の文脈で点検する | subagent (会話を引き継がない種類)。進行役と同じ上位モデルでよい | 新しい `codex exec` プロセスを囲いの外で起動する (`review.md` §Codex)。subagent で点検した結果は「未検品」として扱う (会話を引き継がない起動であることを記録で示せないため)。同上 |

- 正直な注記: Codex の Astra (`gpt-6-astra`、effort high) でも全工程が動く設計だが、Opus 5.5 (high) より品質が少し落ちる (提供者の評価)。差の観察は試験記録で更新する。README にも同じことを書く。
- モデルの選び方は各ツールの設定に従う (Claude Code はモデル選択と effort の設定、Codex は `-m` か設定ファイルの `model` と `model_reasoning_effort`)。検品役を別プロセスで起動する時も同じ指定を `codex exec` に付ける。`review.md` §起動の仕方と `html-contract.md` §5.1 の `codex exec` の例には、この表と同じ `-m gpt-6-astra -c model_reasoning_effort="high"` を書いてある (例のとおりに打つと Codex の既定のモデルで検品してしまうのを防ぐため)。モデルを変える時は、この表と 2 つの例を一緒に直す。
- 進行役より弱いモデルを検品役にしない。同じモデルでよい — 大事なのは別の文脈であること。
- 利用者 (人) への質問は進行役だけが行う。subagent や別プロセスは利用者に質問しない。

## 2. 描画 (P6 書き出し)

| 部品 | 状態 | できること | 条件・注意 |
|---|---|---|---|
| HTML → pptx (`scripts/build.py`) | **既定** | 本文がテキストボックス・表のまま直せる pptx と PDF。読み原稿をノートに入れる (形は `html-contract.md`) | Node.js 22+・Chrome・Python 3.10+ (python-pptx)。土台は consulting-pptx-skill (MIT、改変して同梱。著作権表示はリポジトリの NOTICE) |
| Claude Slides / Claude Design | 任意 (本人が選んだ時だけ) | claude.ai 上のスライド編集画面に渡し、そこでクリックしてコメント・直接編集。PowerPoint・PDF・Google スライドに書き出し | **内容が claude.ai (Anthropic のサーバー) に保存される** — 使う前に本人にそう伝え、了承を得る。claude.ai にログインした Claude Code が要る (API キー接続・一部の企業設定では使えない)。受け取る形は 1 枚ずつの決まった HTML (1920×1080)。書き出した pptx が直せる形か・日本語の書体が保たれるかは **実地で確かめるまで未検証**。書き出しは画面操作 |
| Codex Presentations (OpenAI 同梱) | **案内しない** | (動作は確認済み) | 中で使う部品の license が「内部の評価・試験目的のみ、商用・本番不可」。英語前提の文章規則で、頼んでいない AI 画像を足す。利用者に頼まれても、この skill では使わない理由を伝える |

### 2.1 Codex で書き出す時 (囲いの外で実行する)

Codex は、モデルが打つ command を「囲い」(sandbox。作業フォルダの中だけを触れる実行の仕方) の中で動かす。この囲いの中では、書き出しに使う Chrome と LibreOffice が起動しない (macOS で実測: Chrome は異常終了、LibreOffice は終了コード 134)。そのため Codex では、`scripts/build.py` と、Chrome を使う `scripts/check.py pptx` を **囲いの外で** 実行する。

1. 初めて書き出す前に、利用者に一度だけ伝える: 「PowerPoint と PDF にする部品 (Chrome) は、Codex の安全のための囲いの外で動かす必要があります。このあと Codex が実行してよいかを確かめる画面を出すので、許可してください」。
2. その command を、囲いの外での実行として依頼する (Codex の承認の確認。公式の呼び名は sandbox escalation)。確認が出るのは、対話で使っていて、承認の設定が「必要な時に聞く」(`on-request`) の時。
3. 利用者が許可したら実行する。毎回聞かれたくないと言われたら、確認の画面で今後も許可する方法 (Codex が提案する許可の範囲を受け入れると `~/.codex/rules/default.rules` に書かれる) を案内する。受け入れる前に、範囲がこの skill の script (`python3 <skill>/scripts/build.py` など) だけかを一緒に確かめる。
4. 確認が出ない (`codex exec` などの非対話の実行、承認の設定が「聞かない」(`never`))、または利用者が断った時は、書き出さずに止まる。最後の報告に「**pptx はまだ作れていません**」と書き、理由と今ある物 (HTML のスライド。PDF も作れていなければ「PDF もまだです」) を伝える。利用者が自分の画面で実行できるなら、実行する command を 1 行で渡す。

してはいけないこと:
- その場で別の変換器 (python-pptx などで書いた即席の script) を作って、`build.py` の代わりにすること。`build.py` には日本語の空白・読み原稿・起動待ちの直しと描画の確認が入っていて、即席の物はそれを通らない。
- `build.py` 以外で作った file を納品物にしたり、「検品済み」と呼んだりすること。`check.py manifest` が通るのは `build.py` が書いた記録だけで、それ以外は「未検品」。

Claude Slides / Design を使う時の追加の決まり:
- 検品 (P5) は、渡す前の私たちの HTML と台帳で済ませておく。
- 書き出された pptx は `python3 scripts/check.py pptx <書き出した.pptx> <deck.html>` で欠落・画像化を確かめる。確かめられなければ、その file は「未検品」として渡す。
- 内容の保存先 (claude.ai) と、使ったことを最後の報告に書く。

## 3. 修正の受け方 (P7)

| 環境 | やり方 | 状態 |
|---|---|---|
| どこでも | 会話で「3 枚目の 2 行目を…」と指示してもらう。スライド番号はプレビューと pptx で同じにしておく | 常に使える |
| ChatGPT / Codex のデスクトップアプリ | `python3 scripts/preview.py <案件フォルダ>` で手元に表示用のページを立て (表示される http://127.0.0.1:… の URL)、終わったら `python3 scripts/preview.py <案件フォルダ> --stop` で止める。アプリ内のブラウザで開き、Annotate で要素をクリックしてコメント → チャットで「コメントを反映して」 | 公式の手順にある機能。localhost で使える旨の記載あり、file:// は記載なし。企業の管理設定で制限されることがある。実機での確認は未了 (利用者テスト U-03) |
| Claude Code のデスクトップアプリ | ブラウザ欄で deck.html (またはプレビューの URL) を開き、要素選択 (Cmd+Shift+S) で指してから指示する | 要素選択の機能はアプリにあるが、選んだ内容が指示に添えられるかは未確認。うまく伝わらなければ会話で番号を言ってもらう |
| CLI だけの環境 | 会話で指示してもらう | 常に使える |

画面で指された内容 (要素の文字・場所) は、deck.html の該当箇所に対応させてから直す。どこか分からなければ、候補を 2〜3 示して確かめる。

## 4. 部品を差し替える時

1. `ports.md` で、その工程の入力・出力・失敗時の契約を確かめる。
2. 架空の案件で 1 回通し、出力を `scripts/check.py` (pptx なら `check.py pptx`) で確かめる。
3. この表の行を書き換える。確かめた日と、確かめた事実・確かめていない事実を分けて書く。
4. 実地で確かめていない部品は「未検証」と書き、利用者に「対応」と言わない。
5. 案件では、使った部品を BRIEF の環境欄に書く。

## 出典

- 既定の変換器: carnot-tech/consulting-pptx-skill (MIT)。日本語の和文デッキで、文字の画像化 0・表はネイティブ・はみ出し 0 を確認 (提供者の実走、2026-10-18)
- Claude Slides / Design の入力形式・保存先・利用条件: Claude Code の artifacts の公式 docs (2026-10-18 時点) と提供者の確認。書き出しの編集性は未検証
- Codex Presentations の license と挙動: 提供者の実走 (2026-10-18、`codex exec`)
- Codex の囲いの中で Chrome・LibreOffice・`codex exec` が起動しないこと: 提供者の受け入れ試験 (2026-10-18、Codex CLI 0.163、workspace-write)。囲いの外での実行の承認・許可の規則: https://learn.chatgpt.com/docs/agent-approvals-security と https://learn.chatgpt.com/docs/agent-configuration/rules (2026-10-19 取得)。囲いの中で Chrome を動かす設定は公式 docs に無い
- Annotate: ChatGPT の Browser と annotations の公式 docs (2026-10-18 時点)
- Claude Code デスクトップの要素選択: 公式 docs はショートカットの記載のみ。アプリ内に機能があることを提供者が確認 (指示への添付は未確認)
