# review.md — P5 検品 (作り手と別の文脈で点検する)

## 目的

作り手は自分の思い込みに気づけない。検品は、作り手の会話・説明・推論を一切持たない別の文脈が、正本 (BRIEF)・出典台帳・成果物だけを受け取り、原典を開き直して行う。
同じモデルでもよい。同じ会話の続きで自分が点検するのは検品ではない。

## 独立と言える条件

- reviewer は、作り手の会話を引き継がない subagent か、新しく起動した別プロセスである。
- reviewer に渡すのは **3 つの path だけ**: `BRIEF.md`・`ledger.md`・`deck.html`。作り手の感想・「ここは確認済みです」などの説明・途中の下書き・会話の要約・前の回の検品結果は渡さない。
- reviewer は、渡された file から辿れる物 (台帳にある `sources/` の抜き書きと URL、`out/` の書き出し) を自分で開き、skill フォルダの `scripts/check.py` と `references/doctrine.md` を道具として使ってよい。
- reviewer は成果物を直さない。点検結果の file だけを書く。
- 進行役が **独立の記録** (`review/` の JSON。下記) を書き、`check.py review-evidence` が通る。作り手の「点検しました」は証拠にしない。

どれかを満たせない時は、機械チェックと作り手自身の点検をした上で、結果を **未検品** とする (§どちらも使えない時)。

## 手順 (進行役がやること)

案件フォルダで実行する。`<skill>` は skill フォルダの path、`<n>` は何巡目か。

1. 機械チェックを先に通す (落ちたら直してから頼む):
   ```
   python3 <skill>/scripts/check.py deck deck.html
   python3 <skill>/scripts/check.py ledger ledger.md deck.html [配布資料.html ...] [out/<名前>_読み原稿.md]
   python3 <skill>/scripts/check.py pptx out/<名前>.pptx deck.html
   ```
2. 依頼文を `review/request-<n>.md` に書く (下の雛形。path を埋めるだけ)。
3. 起動する (§起動の仕方)。起動した時刻・終わった時刻・終了コード・reviewer の識別子 (subagent の id か、プロセスの pid) を控える。
4. reviewer が `review/review-<n>.md` を書いたことを確かめる。無ければ 1 回だけ起動し直す。だめなら未検品。
5. 独立の記録を `review/` に JSON で書く (§独立の記録)。
6. `python3 <skill>/scripts/check.py review-evidence review` を実行する。通らなければ、その検品は無かったものとして扱う (記録を直せるなら直す。起動し直すか、未検品)。
7. 結論が「直しが必要」なら §直しの回し方。「合格」なら納品へ (SKILL.md 納品、`check.py manifest`)。

## reviewer への依頼文 (review/request-<n>.md)

```markdown
# 検品の依頼 (<案件>, spec_rev <n>, <n> 巡目)

あなたは資料の検品役です。作った人の説明は受け取っていません。次の 3 つの file と、そこから辿れる物だけで判断してください。
- <案件フォルダ>/BRIEF.md
- <案件フォルダ>/ledger.md
- <案件フォルダ>/deck.html

利用者に質問はできません。分からない所は「点検できなかったこと」に書いてください。
成果物は直さないでください。結果は <案件フォルダ>/review/review-<n>.md に書いてください。
判断の軸: <skill>/references/doctrine.md / 点検の項目と結果の形: <skill>/references/review.md の §点検項目 と §結果の形

## やること
1. 機械チェックを自分で実行し、command・終了コード・出力をそのまま記録する:
   python3 <skill>/scripts/check.py deck <案件フォルダ>/deck.html
   python3 <skill>/scripts/check.py ledger <案件フォルダ>/ledger.md <案件フォルダ>/deck.html <ほかの成果物>
   python3 <skill>/scripts/check.py pptx <案件フォルダ>/out/<名前>.pptx <案件フォルダ>/deck.html
2. 台帳の「確認済み」の行は、できる限り原典の URL を開き直して照らす。開けなければ sources/ の抜き書きで照らし、その旨を書く。
3. 点検項目 A〜F を順に見る。
4. 点検した file (deck.html・ledger.md・BRIEF.md・out/ の file) の sha256 を自分で計算して記録する。
5. 結論を「合格」か「直しが必要」で書く。

最後の 1 行: spec_rev: <BRIEF の spec_rev をそのまま>
```

## 点検項目

順番は事実 → 中身 → 見た目。見た目に感心してから事実を見ない。

**A. 原典との一致**
- 台帳で「確認済み」の行ごとに、引用が主張を本当に支えているか。数字・単位・条件・対象・強さ (努力義務/義務、できる/必ず) まで。
- 適用時点: 基準日に有効か。旧制度・公布済み未施行・経過措置・対象違い・年度や地域の違いが無いか (`evidence.md` §6)。
- 引用の無い「確認済み」が無いか。
- 未確認の行が、資料の該当場所で [要確認] になっているか。
- 資料の全部 (タイトル・本文・図表・注記・読み原稿・配布資料) を読み、台帳に載っていない確認が要る主張が無いか。

**B. 言い過ぎ**
- 原典より強い言い方 (「必ずもらえる」「すべての会社が」「罰則がある」が原典に無い)。
- 助成金・補助金の受給を約束する言い方。
- 出典の無い数字・比較・統計。

**C. 要件の充足**
- BRIEF の要件 (B-01…) ごとに、どこで満たしているか (スライド番号) / 満たしていないか。
- 「言わないこと」に触れていないか。出さない固有名・顧問先の個人情報が出ていないか。
- 成果物の組合せが BRIEF の通りか。

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

重さ: 必須 (事実の誤り・未確認なのに [要確認] が無い・要件違反・言わないことに触れた・個人情報) / 推奨 (読みやすさ・判断の軸)

## 点検できなかったこと
- <>

spec_rev: <n>
```

結論が「合格」と言えるのは、必須の指摘が 0 件で、機械チェックが全部通った時だけ。

## 独立の記録

進行役が、起動のたびに `review/` に JSON で書く。項目と file 名の正は `html-contract.md` (`check.py review-evidence` がそれを読む)。中身の意味:

| 項目 | 書くこと |
|---|---|
| method | `subagent` か `fresh-process` |
| 起動した時刻・終わった時刻 | 実際の時刻 (推測で書かない) |
| inputs | 渡した path。`BRIEF.md`・`ledger.md`・`deck.html` の 3 つだけ |
| reviewer の識別子 | subagent なら返ってきた id、別プロセスなら pid |
| exit | 終了コード (subagent で取れない時は html-contract.md の決まりに従う) |
| 結果 | `review/review-<n>.md` |

別プロセスの時は、その実行記録 (`review/run-<n>.jsonl` など) も残す。記録に無いことを「やった」と書かない。

## 起動の仕方

### Claude Code

- 既定: subagent を 1 つ起動する。会話の文脈を引き継がない種類を選ぶ (今の会話を複製する起動の仕方は使わない)。依頼の本文は短く、`review/request-<n>.md` を読んで従うこと、と 3 つの path だけを書く。モデルは作り手と同じ上位 (Opus 5.5、effort high) でよい。
- 返ってきた subagent の id と、起動前後の時刻を独立の記録に書く。
- 代わり: subagent が使えない時は、新しいプロセスとして非対話モード (`claude -p`) で依頼文を渡す。事前に道具の許可を与えないと止まるので、読み取り・`python3` の実行・Web 取得・`review/` への書き込みだけを許可する。出力を `review/run-<n>.json` に保存し、method は `fresh-process`、pid と終了コードを記録する。

### Codex

- subagent が使えるなら、それでよい。ただし Codex の subagent が親の会話をどこまで引き継ぐかは公式 docs に書かれていない (2026-10-18 確認)。使う時は、依頼の本文に `review/request-<n>.md` と 3 つの path だけを書き、「この依頼文と file 以外の前提を使わない」と添える。
- 迷ったら、または subagent が使えない時は、新しい `codex exec` プロセスを起動する。分離が実行記録で示せる。案件フォルダに移ってから:

```
codex exec --json --skip-git-repo-check -C . -s workspace-write \
  -c model_reasoning_effort="high" -o review/last-<n>.md - \
  < review/request-<n>.md > review/run-<n>.jsonl
echo "exit=$?"
```

  - reviewer は依頼文に従って `review/review-<n>.md` を自分で書く。`-o` は最後の返事を別の file (`last-<n>.md`) に残すだけ (review file を上書きさせない)。`--json` の出力 (`run-<n>.jsonl`) が実行記録になる。起動の前後の時刻 (`date` で控える)・reviewer の識別子 (`run-<n>.jsonl` の 1 行目 `thread.started` の `thread_id`。pid を取れるならそれも)・終了コード (`echo "exit=$?"` の値) を独立の記録に書く。method は `fresh-process`。
  - workspace-write の既定ではネットに出られないことがある。原典を開き直させたい時は `-c sandbox_workspace_write.network_access=true` を足す (Codex CLI 0.163 の設定項目にあることを確認済み。版が違う時は効くか確かめる)。効かなければ `sources/` だけで点検させ、結果に「原典の開き直しはしていない」と書かせる。

### どちらも使えない時

機械チェックを作り手が実行し、作り手自身でも A〜F を点検してよい。ただしその結果は「未検品」として扱い、
- `out/` の file 名に `_未検品` を付ける (例 `deck_未検品.pptx`)、
- `versions.md` の状態を「未検品」にする、
- 最後の報告に「別の目での点検ができませんでした。理由: <>。ご自身で特に [要確認] と数字を確かめてからお使いください」と書く。

## 直しの回し方

1. 作り手は指摘を `issues.md` に写し、必須から直す。指摘に反対する時は理由を書いて残す (黙って無視しない)。
2. 直したら台帳と機械チェックをやり直し (`revision.md`)、新しい reviewer (別の文脈) に次の巡を頼む。前の回の検品結果は渡さない (先入観を移さない)。前の指摘が直ったかは、作り手が新しい結果と `issues.md` を突き合わせて確かめる。
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
- 機械抽出の結果を判定の入力にし、実行記録の無い判定を無効にする、点検役に渡す物を絞る、直しは 2 巡までで人に返す: 提供者 (A&A) の社内の検品手順と注意力設計を一般化
- Codex の subagent の既定: https://learn.chatgpt.com/docs/agent-configuration/subagents (2026-10-18 取得)
- `codex exec` の option: Codex CLI の `codex exec --help` (0.163、2026-10-18 時点)
