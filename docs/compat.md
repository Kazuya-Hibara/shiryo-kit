# 対応環境の根拠 (docs/compat.md)

README と [agent-setup.md](agent-setup.md) の「対応環境」の表が、何を根拠に書いてあるかの記録です。調べた日は 2026-10-18 (日本時間)。各社の公式ページだけを根拠にしています。
読み方の注意:

- ページは AI の取得道具で読みました。「」で囲んだ英文はページにあった文そのまま、それ以外は要約です。
- help.openai.com は取得が拒否された (HTTP 403) ため、そこが出典の記述は **(要約で確認)** と書いています。検索結果の要約でしか確かめていないので、使う前にブラウザで開いて確かめ直してください。
- **公式に書かれていないことを推測で埋めた所は (推測)** と書いています。
- どの行も、実際の利用者の環境で入口から成果物まで通す試験 (U-01〜U-04) をまだしていません。README で「未検証」と書いているのはこのためです。

調査の元の記録は、作った側の作業メモ (公開していません) にあります。ここには、その中から公式ページの URL と記述だけを写しています。

---

## 1. skill フォルダの置き場所 (install.sh / install.ps1 が入れる先)

| 道具 | 置き場所 | 根拠 |
|---|---|---|
| Claude Code | `~/.claude/skills/<名前>/SKILL.md` (個人用) | https://code.claude.com/docs/en/skills —「Personal `~/.claude/skills/<skill-name>/SKILL.md`」 |
| Claude Code (Windows) | `%USERPROFILE%\.claude\skills\…` | Windows で `~/.claude` が `%USERPROFILE%\.claude` になる旨は (要約で確認)。補強として https://code.claude.com/docs/en/setup の取り外し手順に `Remove-Item -Path "$env:USERPROFILE\.claude"` がある |
| Codex | `$HOME/.agents/skills` (個人用) | https://learn.chatgpt.com/docs/build-skills —「Codex scans `.agents/skills` in every directory from your current working directory up to the repository root」、USER の欄が `$HOME/.agents/skills`。リンクしたフォルダもたどる |
| Codex (Windows) | `%USERPROFILE%\.agents\skills` | **公式に記載なし (推測)**。Windows の Codex の設定フォルダが `%USERPROFILE%\.codex` であること (https://learn.chatgpt.com/docs/windows/windows-app) から、`$HOME` = `%USERPROFILE%` と推測した |
| 両方 | 同じフォルダの中身をそのまま使える | 共通の規格 https://agentskills.io/specification (frontmatter は name・description・license・compatibility などの規格の項目だけにしている)。Claude Code は `.agents/skills` を公式には読まない (公式 docs に記載なし。GitHub issue https://github.com/anthropics/claude-code/issues/31005 は非公式) ため、install はそれぞれの場所にコピー (またはリンク) する |

Codex を WSL (Windows の中の Linux) で動かす時は、WSL の中の家のフォルダを使い、Windows 版のアプリと設定を共有しない (https://learn.chatgpt.com/docs/windows/windows-app —「it doesn't automatically share configuration, cached auth, or session history with the Windows app」)。WSL で使う時は WSL の中で `./install.sh --codex` を実行する。

## 2. 必要な契約

| 環境 | 根拠 |
|---|---|
| Claude Code (文字で操作する版) | https://code.claude.com/docs/en/setup —「Claude Code requires a Pro, Max, Team, Enterprise, or Console account. The free claude.ai plan does not include Claude Code access.」 |
| Claude のデスクトップアプリの Code | https://code.claude.com/docs/en/desktop-quickstart —「Claude Code requires a Pro, Max, Team, or Enterprise subscription.」。API キーは受け付けない: https://code.claude.com/docs/en/desktop-linux —「Desktop doesn't accept a Claude Console API key directly」(Linux 版のページの記述。macOS・Windows も同じログインの仕方と書かれている) |
| Codex | https://learn.chatgpt.com/docs/pricing —「ChatGPT Work and Codex are included in your ChatGPT Free, Go, Plus, Pro, Business, Edu, or Enterprise plan」。ただし Free・Go は「GPT-6 Luna at Standard speed in the desktop app, subject to rollout」とあり、Plus は CLI・IDE 拡張を含むと書かれている。**Free・Go で CLI が使えるか、おすすめの gpt-6-astra が使えるかは確かめられていない (不明)**。API キーでは CLI・SDK・IDE 拡張が使える (クラウドの機能は使えない) |
| ChatGPT のデスクトップアプリの内蔵ブラウザ (Annotate) | https://learn.chatgpt.com/docs/browser — 契約の条件の記載なし。「Browser isn't available in Codex CLI or the Codex IDE extension.」 |
| Claude Slides (Claude Code から) | https://code.claude.com/docs/en/artifacts の Availability — Pro・Max・Team・Enterprise、`/login` でログインした状態が要る (API キー・Bedrock・Vertex・Foundry では作れない)。CMEK・HIPAA・Zero Data Retention が有効な組織では使えない。`claude -p` では既定で無効。テンプレートは Claude Code v2.1.265 以降。support 側の記事 https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them は全プランと書いており、2 つのページで範囲が違う (README は狭い方に合わせた) |

## 3. Windows

| 環境 | 根拠 |
|---|---|
| Claude Code | https://code.claude.com/docs/en/setup —「You can run Claude Code natively on Windows or inside WSL.」Windows 10 1809 以降 |
| Claude のデスクトップアプリ | https://code.claude.com/docs/en/desktop-quickstart — Windows 版あり (ARM64 版も) |
| Codex | https://learn.chatgpt.com/docs/windows/windows-sandbox —「Use Codex on Windows with the native ChatGPT desktop app, the CLI, or the IDE extension.」。https://learn.chatgpt.com/docs/windows/windows-app — Windows 版アプリで使える機能に「the built-in browser」「skills」が入っている |
| `install.ps1` | **一度も実行していない。** 作った側の Mac に PowerShell が無く、構文の確認もできていない。Windows PowerShell 5.1 で日本語が化けないよう、ファイルは BOM 付きの UTF-8・CRLF で保存してある。リンクは管理者権限の要らないジャンクションで張る |

## 4. 画面で指して直す機能

| 機能 | 公式に書いてあること | 確かめていないこと |
|---|---|---|
| ChatGPT のデスクトップアプリの Annotate | https://learn.chatgpt.com/docs/browser —「Select Annotate in the browser toolbar to enter Annotation mode.」「Click an element, or drag to select an area.」「Write and save your comment.」「Send a message in the chat asking ChatGPT to address the comments.」。例は `http://localhost:3000/settings`。https://learn.chatgpt.com/docs/annotations-extensibility —「Browser annotations work on your site without any code changes.」。Enterprise・Edu では管理者の許可が要る部分がある。内蔵ブラウザは Mac・Windows のアプリにある (要約で確認、https://help.openai.com/en/articles/20001277) | `file://` で開いた HTML で使えるか (記載なし。shiryo-kit は `scripts/preview.py` で `http://127.0.0.1:…` を立てて使う)。実際の操作 (U-03) |
| Claude のデスクトップアプリのブラウザ欄と要素選択 | https://code.claude.com/docs/en/desktop —「The Browser pane can also open static HTML files, PDFs, images, and videos from your project.」。ショートカットの表に「Cmd Shift S — Select an element in the Browser」とあるだけで、何が起きるかの説明は無い。開き方は「Cmd+Shift+B on macOS or Ctrl+Shift+B on Windows」。SSH の作業では使えない | 選んだ要素が次の指示に添えられるか (アプリの中に要素の情報を取る仕組みがあることは作った側が確かめたが、チャットに渡るところまでは確かめていない)。Windows の要素選択のショートカット (記載なし)。実際の操作 (U-03) |

### 試してみる時の手順 (どちらも未検証)

うまく伝わらない時は、スライドの番号を言葉で伝えてください。

- **ChatGPT のデスクトップアプリ (Codex)**: AI に「プレビューを開いて」と頼むと、`http://127.0.0.1:…` で始まる URL が出ます (`scripts/preview.py` が手元だけで動く表示用のページを立てます)。アプリ内のブラウザでそれを開き、ツールバーの「Annotate」で直したい所をクリックしてコメントを書き、チャットで「コメントを反映して」と送ります。終わったら「プレビューを止めて」と頼みます。
- **Claude のデスクトップアプリ (Claude Code)**: ブラウザ欄 (Mac は Cmd+Shift+B、Windows は Ctrl+Shift+B) で資料のページ (`deck.html` かプレビューの URL) を開き、要素の選択 (Mac は Cmd+Shift+S) で直したい所を選んでから、チャットで指示します。

## 5. 描画の部品 (任意)

| 部品 | 扱い | 根拠 |
|---|---|---|
| Claude Slides | 任意で案内する (本人が頼んだ時だけ) | 書き出し: https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them —「Decks export to PowerPoint and PDF, or go straight to Google Slides as editable files.」(「editable」と書かれているのは Google スライドだけ)。保存先: https://code.claude.com/docs/en/artifacts —「Artifact content is stored on Anthropic-operated infrastructure and is visible only to authenticated members of the publishing organization and the people they share it with, unless the artifact is shared publicly.」。**書き出した PowerPoint が直せる形か・日本語の書体は確かめていない** |
| Codex Presentations | 案内しない | 作った側の Mac で `codex exec` から実際に動かし、直せる日本語の pptx が出ることは確かめた。ただし中で使う部品 `@oai/artifact-tool` の LICENSE.md に「solely for internal evaluation and testing purposes」「You may not ... Use the Software for production, commercial, or benchmarking purposes」とある。ほかに、文章の決まりが英語向けで、頼んでいない AI 画像を足した |
| 既定の書き出し (HTML → pptx) | 既定 | carnot-tech/consulting-pptx-skill (MIT) を元に直して同梱 (NOTICE)。作った側の Mac で、7 枚の日本語の資料を書き出し、文字の画像化 0・表は PowerPoint の表・はみ出し 0 (LibreOffice で描いて確認)。実際の PowerPoint では未確認 (U-02) |

## 6. まだ残っている利用者テスト

| ID | 何を確かめるか | 終わったら README のどこが変わるか |
|---|---|---|
| U-01 | チャット版を実際の ChatGPT・Claude・Gemini に貼り、入口から成果物まで通るか | chat/README.md の対応環境の表の「未検証」 |
| U-02 | 書き出した pptx を実際の PowerPoint (Windows・Mac) で開いて、崩れと直しやすさ | README と agent-setup.md の「PowerPoint で開いた時の崩れは…」の段落と、各行の検証状況 |
| U-03 | ChatGPT のデスクトップアプリの Annotate と、Claude のデスクトップアプリの要素選択で、実際に直せるか | agent-setup.md の「直したい時」の「未検証」と、対応環境の表の「使えない・弱い機能」 |
| U-04 | 初めての士業の方 (同じような立場の 2〜3 名) が、迷わず使えるか・信用できると感じるか | README 全体の書き方と、各行の検証状況 |
| U-05 | Claude の Cowork と ChatGPT の Work に `shiryo-kit-skill.zip` を入れ、入口から成果物まで通るか (スキルが入るか・Chrome が動くか、動かない時の予備の書き出し・PDF・別の AI による点検・メモの引き継ぎ) | README の「おすすめの使い方」の最初の注記 (ブラウザ版で通した・デスクトップアプリは未確認) と、対応環境の表の Cowork・Work の行 |

あわせて、利用者テストの前に作った側が確かめておくこと (README の「未検証」は外さない):

- `install.ps1` を Windows (Windows PowerShell 5.1 と PowerShell 7) で実行し、コピー・入れ替え・リンク・止まる場合を確かめる。
- Windows の Codex が `%USERPROFILE%\.agents\skills` を読むか (§1 の推測)。
- Codex で Free・Go の契約のまま gpt-6-astra を選べるか (§2)。
- Claude Slides から書き出した pptx を `scripts/check.py pptx` で確かめ、文字が直せる形か・日本語の書体を記録する (§5)。

## 7. Claude の Cowork・ChatGPT の Work (README の「おすすめの使い方」)

調べた日は 2026-10-19 (日本時間)。Claude のヘルプは日本語のページがあったので、画面の名前は日本語のページの言葉を使いました。ChatGPT は英語のページしか確かめられていません (help.openai.com は取得が拒否された)。

| 書いたこと | 根拠 |
|---|---|
| Claude: スキルは ZIP でアップロードする。「カスタマイズ」→「スキル」→「+」→「+ スキルを作成」→「スキルをアップロード」 | https://support.claude.com/ja/articles/12512180 (「Claudeでスキルを使用する」) —「スキルフォルダーをZIPファイルとしてパッケージ化します。」「カスタムスキルを追加するには、「+」ボタンをクリックしてから「+ スキルを作成」をクリックします。」「「スキルをアップロード」を選択します。」。手順の行は英語の名前で「Customize > Skills」、削除の手順では「カスタマイズ > スキル」と書かれている |
| Claude: 「設定」→「機能」で「コード実行とファイル作成」を ON | 同じページ —「個別のFree、Pro、Maxプランの場合: Settings > Capabilitiesに移動し、コード実行とファイル作成が有効になっていることを確認します。」、トラブルシューティングに「設定 > 機能（Free、Pro、Max）」。Team は「組織レベルでデフォルトで有効」、Enterprise はオーナーが有効にする |
| Claude: ZIP の形・description は 200 字まで | https://support.claude.com/ja/articles/12512198 (「カスタムスキルの作成方法」) —「フォルダ名がスキルの名前と一致することを確認します。」「ZIPはスキルフォルダをルートとして含める必要があります（サブフォルダではなく）。」、description は「（最大 200 文字）」。`tools/build_skill_zip.py` はこれに合わせる |
| Cowork は有料プランだけ。メッセージ欄で「Cowork」を選ぶ | https://support.claude.com/ja/articles/13345190 (「Claude Coworkを始める」) —「Claude Coworkは有料プラン（Pro、Max、Team、Enterprise）で利用できます。」「メッセージボックスで「Cowork」を選択します。」。「Chat」と「Cowork」の選択が無い新しい画面では「すべての会話がCoworkタスクを実行できます」 |
| Cowork の作業は Anthropic のサーバーで動き、アカウントに保存される | 同じページ —「Claudeの作業はAnthropicのサーバー上の隔離された環境で実行され、セッションとファイルはClaudeアカウントに保存されます。」 |
| ChatGPT: 自分のスキルをそのまま使えるのはデスクトップアプリ | https://learn.chatgpt.com/docs/build-skills —「Standalone skills are available in the ChatGPT desktop app, Codex CLI, and IDE extension. Skills bundled in plugins are also available in Chat and Work across ChatGPT on the web, desktop, and mobile.」「In the ChatGPT desktop app, open Skills in the sidebar to view and explore skills created across your projects.」「In ChatGPT, type @ to select a skill.」 |
| ChatGPT: 「Work」に切り替える | https://learn.chatgpt.com/docs/get-started-with-work —「First, switch to Work.」 |
| ChatGPT: Work は無料を含む全プランに入っている | https://learn.chatgpt.com/docs/pricing —「ChatGPT Work and Codex are included in your ChatGPT Free, Go, Plus, Pro, Business, Edu, or Enterprise plan」。Free・Go は「GPT-6 Luna at Standard speed in the desktop app, subject to rollout」 |

**実機で確かめたこと (2026-10-19、作った側、ブラウザ版の claude.ai と chatgpt.com。架空の依頼で 1 回ずつ):**

- ChatGPT は、左端のアイコンの列から開く「カスタマイズ」→「スキル」→「追加」→「コンピューターからアップロード」で ZIP を入れられた (.zip・25 MB まで)。「プラグイン」の画面の「プラグインアーカイブをアップロード」とは別。ブラウザ版でも、入れたスキルを Work で使えた (「@shiryo」で選べる)。
- Claude は「Customize」→「Skills」→「Add」→「Upload skill」で入れられ、Cowork の作業で使われた (右の欄の「Context」→「Skills」に表示)。Cowork の既定「Manual」では、コマンドごとに許可を求めて止まる。
- どちらも Chrome があり、確認つきの書き出しになった。別の AI による点検は、Cowork ではできた。Work では `codex exec` が 45 秒の間に何も出さず (作り手の AI が自分で 45 秒に区切った)、未検品になった (原因は確かめていない)。
- 入るスキルの名前は ZIP の中の SKILL.md から付いた (ZIP の名前ではない)。

**確かめられなかったこと (README では「未確認」と書いた):**

- デスクトップアプリ (Claude.app・ChatGPT.app) の画面と名前。上の確認はブラウザ版だけ。
- ChatGPT で ZIP からスキルを追加する手順の公式の説明 (画面はブラウザ版で確かめた。上)。公式のページ (learn.chatgpt.com) には、プラグインの作り方 (https://developers.openai.com/plugins/build/plugins の `plugin.json` と `skills/<名前>/SKILL.md`、手元の marketplace の JSON を置いてデスクトップアプリを再起動する) と、会話で作る「Plugin Creator」(https://learn.chatgpt.com/docs/build-plugins) しか書かれていない。ふつうの利用者が ZIP を入れる手順は help.openai.com にあるらしいが、開けなかった。
- `install.sh --codex` で `~/.agents/skills` に入れたスキルが、ChatGPT のデスクトップアプリの Work からも見えるか (公式に書かれているのは Codex が読むことだけ)。
- ChatGPT の無料・Go のプランで自分のスキルを入れられるか。Work で gpt-6-astra を選べるか。
- Claude で、アップロードした自分のスキルが Cowork の作業の中でも使われるか: 公式に一文は無いが、2026-10-19 にブラウザ版で使われることを確かめた (上)。
- Cowork・Work の中に Chrome・LibreOffice・Node.js があるか (どの公式ページにも書かれていない。2026-10-19 のブラウザ版では Chrome があった。いつもあるかは分からない)。無い時の予備の書き出しは shiryo-kit 側で用意した (README の「Cowork・Work の中で起こりうること」)。

