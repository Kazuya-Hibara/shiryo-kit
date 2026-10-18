# review.md — P5 検品 (作り手と別の文脈で点検する)

## 目的

作り手は自分の思い込みに気づけない。検品は、作り手の会話・説明・推論を一切持たない別の文脈が、正本 (BRIEF)・出典台帳・成果物だけを受け取り、原典を開き直して行う。
同じモデルでもよい。同じ会話の続きで自分が点検するのは検品ではない。

## 独立と言える条件

- reviewer は、作り手の会話を引き継がない subagent か、新しく起動した別プロセスである (Codex の subagent は引き継がないことを示せないので当てはまらない。§起動の仕方 Codex)。
- reviewer に渡すのは **3 つの path だけ**: `BRIEF.md`・`ledger.md`・`deck.html`。配布物 (配布 1 枚など) があれば、`review_record.py start … --extra <配布物の HTML>` で足し、依頼文の雛形の「配布物:」の行を残す (無ければその行を消す)。配布物を入れずに検品すると、`check.py manifest` は配布物を「未検品」にする。作り手の感想・「ここは確認済みです」などの説明・途中の下書き・会話の要約・前の回の検品結果は渡さない。
- reviewer は、渡された file から辿れる物 (台帳にある `sources/` の抜き書きと URL、`out/` の書き出し) を自分で開き、skill フォルダの `scripts/check.py` と `references/doctrine.md` を道具として使ってよい。
- reviewer は成果物を直さない。点検結果の file だけを書く。
- **独立の記録** (`review/independence-<n>.json`) は `scripts/review_record.py` が取り (起動の時刻・pid・終了コード・出力・渡した file の sha256)、`check.py review-evidence` が通る。進行役は JSON を手で書かない。作り手の「点検しました」は証拠にしない。

どれかを満たせない時は、機械チェックと作り手自身の点検をした上で、結果を **未検品** とする (§どちらも使えない時)。

## 手順 (進行役がやること)

案件フォルダで実行する。`<skill>` は skill フォルダの path、`<n>` は何巡目か。

1. 機械チェックを先に通す (落ちたら直してから頼む):
   ```
   python3 <skill>/scripts/check.py deck deck.html
   python3 <skill>/scripts/check.py ledger ledger.md deck.html [配布資料.html ...] [out/<名前>_読み原稿.md]
   python3 <skill>/scripts/check.py pptx out/<名前>.pptx deck.html
   python3 <skill>/scripts/check.py pii deck.html
   ```
   - `ledger` は台帳の隣の `sources/` (取得した原典の本文) があれば、確認済みの引用をそこと自動で照らす。PDF は `pdftotext` などで .txt にして置く。
   - `pii` は、顧問先名・個人の名前・連絡先が資料に残っていないかの機械の補助 (C の点検の入口。「ここは出してよい」と本人が決めた語は `--allow` で外す)。出た行は本人に確かめる。
2. 依頼文を `review/request-<n>.md` に書く (下の雛形。`<…>` を埋めるだけ)。雛形に無い行 (「特に日付を見て」「今回直した所」「目安の時間」など) を足さない。`<…>` の中にも足さない。作り手の観点が reviewer に移るため。当てはまらない行は書き換えずに消す (pptx が無い時は `check.py pptx` の行と、4. の「・out/ の file」を消す)。雛形に無い行・埋めていない `<…>` があると `review_record.py` の `start`・`run` が止まる。
3. **起動と記録は `scripts/review_record.py` を通す** (§起動の仕方)。時刻・終了コード・reviewer の識別子は script が取る。進行役が時計を見て書いたり、JSON を作ったりしない。
   - subagent: 起動の直前に `review_record.py start review --round <n>`、返事が返った直後に `review_record.py finish review --round <n> --reviewer-id <返ってきた id>`。
   - 別プロセス: `review_record.py run review --round <n> --stdin review/request-<n>.md -- <起動 command>`。
4. reviewer が `review/review-<n>.md` を書いたことを確かめる。無ければ `--force` を付けて 1 回だけ起動し直す。だめなら未検品。
5. `python3 <skill>/scripts/check.py review-evidence review` を実行する (内容は `html-contract.md` §5.1)。通らなければ、その検品は無かったものとして扱う。独立の記録は手で直さない。起動し直すか、未検品。確かめたい時は `review_record.py show review --round <n>`。
6. 結論が「直しが必要」なら §直しの回し方。「合格」なら納品へ (SKILL.md 納品、`check.py manifest`)。

## reviewer への依頼文 (review/request-<n>.md)

```markdown
# 検品の依頼 (<案件>, spec_rev <n>, <n> 巡目)

あなたは資料の検品役です。作った人の説明は受け取っていません。次の 3 つの file と、そこから辿れる物だけで判断してください。
- <案件フォルダ>/BRIEF.md
- <案件フォルダ>/ledger.md
- <案件フォルダ>/deck.html
- 配布物: <案件フォルダ>/<配布物の HTML>

利用者に質問はできません。分からない所は「点検できなかったこと」に書いてください。
成果物は直さないでください。結果は <案件フォルダ>/review/review-<n>.md に書いてください。
判断の軸: <skill>/references/doctrine.md / 点検の項目と結果の形: <skill>/references/review.md の §点検項目 と §結果の形
`review/independence-<n>.json` と `review/run-<n>.*` は記録用です。開いても書き換えないでください。

## やること
1. 機械チェックを自分で実行し、command・終了コード・出力をそのまま記録する:
   python3 <skill>/scripts/check.py deck <案件フォルダ>/deck.html
   python3 <skill>/scripts/check.py ledger <案件フォルダ>/ledger.md <案件フォルダ>/deck.html <ほかの成果物>
   python3 <skill>/scripts/check.py pptx <案件フォルダ>/out/<名前>.pptx <案件フォルダ>/deck.html
   python3 <skill>/scripts/check.py pii <案件フォルダ>/deck.html
2. 台帳の「確認済み」の行は、できる限り原典の URL を開き直して照らす。開けなければ sources/ の抜き書きで照らし、その旨を書く。
3. 点検項目 A〜F を順に見る。
4. 点検した file (deck.html・ledger.md・BRIEF.md・out/ の file) の sha256 を自分で計算して記録する (deck.html の sha256 は必ず結果に書く)。
5. 結論を「合格」か「直しが必要」で書く。

最後の 1 行: spec_rev: <BRIEF の spec_rev をそのまま>
```

## 点検項目

順番は事実 → 中身 → 見た目。見た目に感心してから事実を見ない。

**A. 原典との一致**
- 台帳で「確認済み」の行ごとに、引用が主張を本当に支えているか。数字・単位・条件・対象・強さ (努力義務/義務、できる/必ず) まで。
- 適用時点: 基準日に有効か。旧制度・公布済み未施行・経過措置・対象違い・年度や地域の違いが無いか (`evidence.md` §6)。
- 公布済み・未施行の日付: 基準日より後に始まる制度・段階的な適用の日 (「2027年10月から」など) が、出てくる所ごとに「◯年◯月◯日施行予定」か「◯年◯月施行予定」(`evidence.md` §6) と書き分けてあるか。タイトル・図・表・読み原稿の中も見る。無ければ必須。
- 根拠の印 (【法律】などを使っている時): 印と台帳の出典の種類が合っているか。条文でない通達・Q&A・リーフレットの内容に【法律】が付いていないか (`evidence.md` §2b)。
- 引用の無い「確認済み」が無いか。
- 未確認の行が、資料の該当場所で [要確認] になっているか。
- 資料の全部 (タイトル・本文・図表・注記・読み原稿・配布資料) を読み、台帳に載っていない確認が要る主張が無いか。

**B. 言い過ぎ**
- 原典より強い言い方 (「必ずもらえる」「すべての会社が」「罰則がある」が原典に無い)。
- 原典の限定を落とした言い方 (「原則として」「一定の要件を満たす場合」「〜できる」「努力義務」を消した・強めた)。
- 助成金・補助金の受給を約束する言い方。
- 出典の無い数字・比較・統計。

**C. 要件の充足**
- BRIEF の要件 (B-01…) ごとに、どこで満たしているか (スライド番号) / 満たしていないか。
- 「言わないこと」に触れていないか。出さない固有名・顧問先の個人情報が出ていないか (`check.py pii deck.html` の結果を見た上で、機械が拾えない呼び方も目で見る)。
- 成果物の組合せが BRIEF の通りか。
- 受け手 (BRIEF の persona) に含まれる人 (短時間のパート・週の日数が多い人・個人事業主など) が、資料の条件の書き方で、対象から外れて (または対象に入って) 読めないか。原典の条件が 2 つ以上ある時 (「◯時間未満で、かつ、◯日以下」のような形)、片方だけを書いていないか。

**D. 受け手として読む**
- BRIEF の persona になったつもりで、表紙から最後まで読む (読み原稿があれば、話されるつもりで)。
- 分からない言葉、引っかかる所、出てくる疑問、誤解しそうな所をスライド番号つきで挙げる。
- 読み終えた時、「持ち帰らせたい行動」をしたくなるか。何が足りないか。
- 場面 (話す/配る、時間) に密度と枚数が合っているか。

**E. 資料の判断の軸** (`doctrine.md`)
- タイトルだけを順に読んで話が通るか。各タイトルが結論を 1 文で言っているか (表紙・目次・章扉は除く)。
- 結論が最初の数枚で分かるか。1 枚に話が 2 つ入っていないか。
- 語調がそろっているか。BRIEF の口調 (§6) と合っているか。

**F. 機械チェック**
- 実行した結果をそのまま記録し、FAIL があれば指摘にする。
- 機械の誤検知と見える FAIL (例: 出典の URL の中の数字を電話番号と読んだ) も、消さずに「必須」の指摘として残し、「誤検知の疑い: <理由>」と書く。作り手は本人への報告で、指摘の数を検品結果と同じに数え、その指摘を「機械の誤検知と判断したもの (理由)」として別に挙げる。「問題がなかったこと」には入れない (報告と検品結果の数が食い違うと、本人が検品結果を確かめられない)。
- 閉じ方: `pii` の誤検知なら、本人に語を見せて了承をもらい、検査するフォルダ直下の `pii-allowlist.txt` に足して機械チェックをやり直す (顧問先側の個人の情報は足さない)。通れば次の巡でその指摘は直ったものとして扱う。資料を直さずに通す方法が無い誤検知 (了承がもらえない時も) は、合格にせず、理由を添えて「未検品」として渡す (§どちらも使えない時)。

## 結果の形 (review/review-<n>.md)

```markdown
# 検品結果 <n> 巡目 — <案件> (spec_rev <n>)

## 結論: 合格 / 直しが必要

## 点検した file
- deck.html sha256: <> / ledger.md: <> / BRIEF.md: <> / out/<file>: <>
- 原典の開き直し: した / できなかった (理由)

## 機械チェック
- `<command>` → 終了コード <n>
  <出力をそのまま>

## 指摘
| 番号 | 重さ | 場所 | 資料の記述 (引用) | 根拠 (B-xx / 台帳 ID / 原典の引用) | 直し方の案 |
|---|---|---|---|---|---|
| 1 | 必須 | 3 枚目 本文 | 「…」 | 台帳 L-04 の引用は「…」 | |

重さ: 必須 / 推奨 (付け方は review.md §重さの決め方)

## 点検できなかったこと
- <>

spec_rev: <n>
```

結論の行は「合格」「直しが必要」のどちらか一方だけを残す (雛形の `合格 / 直しが必要` のままだと、`check.py review-evidence` が未検品にする)。最後の行の `spec_rev:` と、点検した deck.html の sha256 も必ず書く。

結論が「合格」と言えるのは、必須の指摘が 0 件で、機械チェックが全部通った時だけ。

### 重さの決め方

迷ったら必須にする。受け手が間違った行動をとるおそれのある指摘は、直し方が小さくても必須。

**必須**
- 事実の誤り: 数字・単位・日付・対象・条件が原典と違う。
- 言い過ぎ: 原典より強い言い方。原典の「原則として」「一定の要件を満たす場合」「〜できる」「努力義務」を落とした・強めた (例: 原典「原則として」→ 資料は限定なしで言い切り)。条文でない内容に【法律】の印を付けた。
- 受け手の一部を間違って外す・含める抜け: 条件の片方だけを書き、聞いた人の一部が「自分は対象外」(または「自分も対象」) と誤解しうる (例: 原典の対象が「A か B のどちらかに当たる人」なのに、資料は A だけを書いた。B だけに当たる人が対象外と読める)。その人たちが受け手に含まれるか BRIEF から分からない時も必須にする。
- 公布済み・未施行の内容を今の制度として書いた、または未施行の日付に「施行予定」が無い。
- 未確認なのに [要確認] が無い。要件 (BRIEF) 違反。言わないことに触れた。個人情報・出さない固有名が出た。

**推奨**
- 事実・条件・強さは原典どおりで、受け手が誤解しないが、読みやすさ・判断の軸 (`doctrine.md`)・語調・見た目に直す余地がある。

指摘の中で自分が「対象から外してしまうおそれ」「誤解されるかもしれない」「原典より強い」と書いたものは、推奨にしない (必須)。どの巡の reviewer も、この基準で重さを付ける (巡によって同じ種類の指摘の重さを変えない)。

## 独立の記録

`review/independence-<n>.json` は `scripts/review_record.py` が書く (AC-07: 検品が別の文脈で行われたことを、作り手の自己申告ではなく script が取った記録で示す)。項目と file 名の正は `html-contract.md` §5.1 (`check.py review-evidence` がそれを読む)。進行役が知っておくこと:

| 項目 | 誰が決めるか |
|---|---|
| method (`subagent` か `fresh-process`) | `start` は subagent、`run` は fresh-process。script が書く |
| 起動した時刻・終わった時刻 | script が時計から取る (`start`/`finish`、`run` の前後) |
| inputs | `BRIEF.md`・`ledger.md`・`deck.html` の 3 つ。script が path と sha256 を取る。配布物は `--extra` で `extra_inputs` に入る |
| reviewer の識別子 | subagent なら返ってきた id (`finish --reviewer-id` で渡す)。別プロセスなら codex の `thread_id`・claude の `session_id`、取れなければ `pid:<番号>` (script が拾う) |
| exit | `run` は script が終了コードを取る。subagent は終了コードが無いので `exit_status: null` と理由 (`exit_note`) を記録する。「返事が返り、結果の file がある = 正常終了」として扱う決まり |
| 結果 | `review/review-<n>.md` (終了時点の sha256・更新時刻を記録) |

別プロセスの出力 (`review/run-<n>.jsonl`・`run-<n>.stderr.log`) は `run` が残す。subagent の実行記録の file があれば `finish --transcript <file>` で渡すと、記録が強くなる。

限界: 記録が示すのは「script が起動・時刻・出力・sha256 を取った」ところまで。subagent の識別子は進行役が `finish --reviewer-id` で渡す値なので、同じ reviewer の使い回しを見つけられるのは、進行役が本当の id を渡した時だけ。subagent が作り手の会話を引き継いでいないことは記録からは分からない (だから上の「独立と言える条件」と起動の仕方を守る)。JSON を手で偽造することは防げない — 手で書かない・直さないのは進行役の決まり。

## 起動の仕方

### Claude Code

- 既定: subagent を 1 つ起動する。会話の文脈を引き継がない種類を選ぶ (今の会話を複製する起動の仕方は使わない)。依頼の本文は短く、`review/request-<n>.md` を読んで従うこと、と 3 つの path だけを書く。モデルは作り手と同じ上位でよい (`adapters.md` §1)。
- 起動の直前に `review_record.py start review --round <n>`、返事が返った直後に `review_record.py finish review --round <n> --reviewer-id <subagent の id>` を実行する。時刻は script が取る。
- 代わり: subagent が使えない時は、新しいプロセスとして非対話モード (`claude -p`) で依頼文を渡す。事前に道具の許可を与えないと止まるので、読み取り・`python3` の実行・Web 取得・`review/` への書き込みだけを許可する。`review_record.py run` に包んで起動すると、時刻・pid・終了コード・出力を script が記録する (method は `fresh-process`):

```
python3 <skill>/scripts/review_record.py run review --round <n> --stdin review/request-<n>.md -- \
  claude -p --output-format json --allowedTools "Read,Write,Bash(python3:*),WebFetch"
```

### Codex

- 既定: 新しい `codex exec` プロセスを起動する。分離が実行記録で示せる。
- **この command は Codex の囲い (sandbox) の外で実行する。** 囲いの中から `codex exec` を起動すると、必ず失敗する (`failed to initialize in-process app-server client: Operation not permitted`。Codex CLI 0.163 で実測)。書き出しと同じく、利用者に一度だけ許可をもらって囲いの外で実行する (`adapters.md` §2.1 の 1〜3)。許可の確認が出ない・断られた時は、検品は「未検品」。
- subagent は検品に使わない。Codex の subagent には、作り手の会話を引き継がずに起動する指定が公式 docs に無く (2026-10-19 確認)、起動の記録 (`exec --json` の出力) にも起動の引数が残らない。つまり別の文脈だったことを記録で示せない。subagent に点検させた時は、その結果を作り手の点検と同じ扱いにし、状態は「未検品」とする (`review_record.py start`/`finish` で記録しても「検品済み」と言わない)。
- 案件フォルダに移ってから:

```
python3 <skill>/scripts/review_record.py run review --round <n> --stdin review/request-<n>.md -- \
  codex exec --json --skip-git-repo-check -C . -s workspace-write \
  -m gpt-6-astra -c model_reasoning_effort="high" -o review/last-<n>.md -
```

  - モデルと考える深さ (`-m gpt-6-astra -c model_reasoning_effort="high"`) は `adapters.md` §1 と同じ。省くと Codex の既定のモデルで検品してしまう。
  - `codex exec` を `review_record.py run` に包む。`> review/run-<n>.jsonl` や `echo "exit=$?"` は要らない: 標準出力は `review/run-<n>.jsonl`、標準エラーは `review/run-<n>.stderr.log` に script が残し、時刻・pid・終了コードも script が記録する。reviewer の識別子は、出力の `thread.started` の `thread_id` を script が拾う。method は `fresh-process`。
  - reviewer は依頼文に従って `review/review-<n>.md` を自分で書く。`-o` は最後の返事を別の file (`last-<n>.md`) に残すだけで、`check.py review-evidence` は見ない (review file を上書きさせないための指定)。
  - workspace-write の既定ではネットに出られないことがある。原典を開き直させたい時は `-c sandbox_workspace_write.network_access=true` を足す (Codex CLI 0.163 の設定項目にあることを確認済み。版が違う時は効くか確かめる)。効かなければ `sources/` だけで点検させ、結果に「原典の開き直しはしていない」と書かせる。

### どちらも使えない時

機械チェックを作り手が実行し、作り手自身でも A〜F を点検してよい。ただしその結果は「未検品」として扱い、
- `python3 <skill>/scripts/build.py deck.html --out out --unreviewed` で書き出し直す。file 名が `<名前>_未検品.*` になり、pptx の各スライドの右上・文書のプロパティ (題名・キーワード・分類)、PDF の各ページの右上にも「未検品」が入る。印の無い `deck.pptx`・`deck.pdf` は渡さない (同じ `out/` に残っていれば消すか `out/` の外に移す。file 名を変えるだけ・複製するだけでは印が中身に入らない)。この場合 `check.py manifest out review` は「未検品」で FAIL するのが正しい動き (渡してよいのは「未検品」と明記した時だけ)、
- `versions.md` の状態を「未検品」にする、
- 最後の報告に「別の目での点検ができませんでした。理由: <>。ご自身で特に [要確認] と数字を確かめてからお使いください」と書く。

## 直しの回し方

1. 作り手は指摘を `issues.md` に写し、必須から直す。指摘に反対する時は理由を書いて残す (黙って無視しない)。
2. 直したら台帳と機械チェックをやり直し (`revision.md`)、新しい reviewer (別の文脈) に次の巡を頼む。前の巡の reviewer に続きを頼まない (前の結論と直しの説明を持ったまま見ることになる。reviewer の識別子が前の巡と同じだと `check.py review-evidence` が FAIL にする)。前の回の検品結果は渡さない (先入観を移さない)。前の指摘が直ったかは、作り手が新しい結果と `issues.md` を突き合わせて確かめる。
3. 直しは既定で 2 巡まで。2 巡目でも必須の指摘が残ったら、それ以上回さずに本人に見せる: 「点検で次の指摘が残っています。どうするか決めてください」。本人が「このままでよい」と言ったら、その言葉を BRIEF の決定ログに残し、状態は「検品済み・指摘が残っています」とする。

## 納品の前

`python3 <skill>/scripts/check.py manifest out review` を実行する。渡す file の sha256 が、検品した file の sha256 と一致する時だけ通る。通らなければ、もう一度検品するか「未検品」として渡す。

## 利用者への伝え方

- 合格: 「別の目で点検し、指摘はありませんでした (点検の記録: review/review-<n>.md)」
- 指摘が残った: 「点検で <n> 件の指摘が残っています。一覧です: …」
- 未検品: 上の「どちらも使えない時」の文

## 出典

- 作り手と別の目が成果物だけを読み、間違った推測が効く所だけを返す: obra/superpowers の builder check (MIT)
- 仕様に合っているかと品質を分けて点検する: obra/superpowers `subagent-driven-development` の reviewer (MIT)
- 証拠を見ずに完了と言わない: obra/superpowers `verification-before-completion` (MIT)
- 作り手の申告は証拠ではない: BMAD-METHOD `claims-check` (MIT)
- 受け手になって読む点検: anthropics/skills `doc-coauthoring` の Reader Testing の考え方 (文言は使っていない)
- 機械抽出の結果を判定の入力にし、実行記録の無い判定を無効にする、点検役に渡す物を絞る、直しは 2 巡までで人に返す: 提供者の社内の検品手順と注意力設計を一般化
- Codex の subagent の既定 (親の会話を引き継ぐかの記載が無い・起動の指定は名前・説明・指示・モデル・考える深さだけ): https://learn.chatgpt.com/docs/agent-configuration/subagents (2026-10-18 取得、2026-10-19 再確認)
- Codex の囲いの外での実行: https://learn.chatgpt.com/docs/agent-approvals-security (2026-10-19 取得)。囲いの中で `codex exec` が起動しないこと: 提供者の受け入れ試験 (2026-10-18)
- `codex exec` の option: Codex CLI の `codex exec --help` (0.163、2026-10-18 時点)
