# html-contract.md — HTML の書き方・出典台帳の書式・scripts の使い方

この file は `scripts/` が読む形の正本。ここと scripts の動きが違ったら、scripts の動きが正しい (この file を直す)。
path は skill フォルダからの相対 path。案件フォルダで実行する時は `python3 <skill>/scripts/...` と書く。

## 1. スライドの HTML

### 1 枚の区切り

- 1 枚 = `<section class="s"> … </section>`。入れ子にしない (scripts は `section.s` / `section.slide` / `.slide` のうち、別のスライドの内側に無いものを 1 枚と数える)。
- 大きさは 16:9 (`338.67mm × 190.5mm`)。部品集の CSS (`assets/parts/`) をそのまま使えば満たす。手書きの HTML で部品集の CSS を使わないと `check.py deck` が「16:9 サイズ…」で FAIL する。
- 表紙は `<section class="s cover">`、章扉は `<section class="s chap">`。この 2 つはタイトル必須・結論型タイトルの検査から外れる。
- タイトル = 各枚の `h1` (または `.ttl` / `.title` / `.msg` を付けた要素の最初の 1 つ)。結論を 1 文で書く (`doctrine.md` §3)。
- 表は `<table>` で書く (pptx で PowerPoint の表になる)。図は SVG・画像にしてよいが、中の文字は直せない絵になる。読ませる文字は図の外のテキストに置く。
- 文書の題 `<head><title>` は pptx・PDF の文書の題になる。`<meta charset="utf-8">` を入れる。

### 部品から組み立てる

```
python3 scripts/new_deck.py --list                                   # 部品の番号と型名 (b01〜b27・m01〜m35)
python3 scripts/new_deck.py --parts b01,b03,b06,b09,b10 --title "資料名" -o deck.html
```

- 出来た HTML は見本の文字 (「Text 1」「ラベル 1」など) が入っている。全部書き換える (残ると `check.py deck` が FAIL)。
- 各枚に空の `<aside class="notes"></aside>` が入っている。読み原稿をここに書く。

### 読み原稿 (スピーカーノート)

- 各枚の `<section>` の内側に `<aside class="notes"> … </aside>` を置く (1 枚に複数あってもよい。順につなぐ)。
- 段落は `<p>` か `<br>` か `<li>` で分ける。画面にも印刷にも出ない (`aside.notes{display:none}`)。
- 代わりに `<section class="s" data-notes="…">` の属性でもよい。両方あれば data-notes → aside の順につなぐ。
- 読み原稿は pptx のノート・`out/<名前>_読み原稿.md` になる。`check.py ledger` の照合の対象。`check.py deck` は避ける言い回しだけを読み原稿にも当てる (体裁の規約は当てない)。

### 空白と改行

- ソースの改行は、和文と和文の間では詰める (「就業\n規則」→「就業規則」)。和文の 1 行をソースで折り返してもよいが、意図しない詰まりを避けるため、文の途中で改行しないのが安全。
- 作者が打った空白 (半角・全角 U+3000・`&nbsp;`) は残る。見出しの「経営者向け　第2回」の全角空白は pptx でもそのまま。
- 打った行頭記号 (・ • –) は pptx の箇条書きに置き換わる。1 つの資料で記号の形をそろえる。

### [要確認] の出し方

- 台帳で「未確認」の主張は、資料の同じ場所に `[要確認]` を出す (`［要確認］` `【要確認】` も可)。
  - スライド本文: 同じ文章の塊 (同じ `<p>`・`<li>`・`<td>`) の中。
  - 読み原稿・配布資料: 同じ行 (同じ段落)。
- 未確認の数字を作らない (`evidence.md`)。数字を書かずに「[要確認] 最新の率は協会けんぽの料率表で確かめる」のように書いてよい。

### 出典の行 (`.src`) の日付

出典の行に日付を書く時は、「制度の基準日」(どの日の制度で説明しているか) と「原典の確認日」(原典を開いて確かめた日) を言葉で書き分ける。例: `出典: 厚生労働省「…」https://… (原典の確認日 2026年10月18日)。※2026年11月20日 (セミナー当日) 時点の制度で説明しています。` 「◯月時点の情報」とだけ書かない (確認日と並ぶと矛盾に読まれる)。決まりの理由は `evidence.md` §6「紙面の出典の注記」。型の見本 (`assets/kata/*/sample.html`) も同じ書き方にしてある。

### 照合から外す部品

`check.py ledger` は次の部分の数字を台帳と照らさない (ページ番号・日付の帯・出典行など、主張ではない所):
- class が `foot` `bar` `logo` `date` `tn` `tp` `ref` `no` `cn` `cno` `src` `pageno` の要素とその中身
- `data-ledger="skip"` を付けた要素とその中身
- Markdown・テキストの成果物では、`<!-- ledger:skip -->` を含む行と HTML コメントの中

主張を含む文に `data-ledger="skip"` を付けない (照合を逃れるための指定は検品で必須の指摘になる)。

## 2. 出典台帳の形式 (ledger.md)

Markdown の表を 1 つ書く。見出し行に「主張」(または「資料での書き方」) と「区分」の列が要る。列の順は自由、無い列は省略できる (下の必須を除く)。

| 列 (別名) | 中身 |
|---|---|
| ID (番号, No) | `L-01` など。重複は FAIL |
| 主張 (内容, 資料での書き方) | 資料に書く主張。数字・日付・率・金額はここに資料と同じ値で書く |
| 表記 (資料での表記) | 資料での別の書き方 (「36人以上」と「36〜50人」など)。照合に使う |
| 区分 (状態) | `確認済み` / `未確認` / `本人提供` (`原典確認済み` = 確認済み、`要確認` = 未確認) |
| 出典URL (出典 URL, URL) | http(s) の URL |
| 取得日 (確認日) | `2026-10-18` の形 |
| 引用 (原文, 該当箇所, 取得した本文の該当箇所 (引用)) | 原典の文をそのまま。複数なら「…」「…」と括弧で分ける |
| 適用時点 (時点) | 施行日・経過措置・対象・未施行かどうか |
| 使用箇所 (場所, ページ) | `p3` / `p3-5` / `3枚目` / `s2 本文` / `p2 原稿`。照合の候補をこのページに絞る |
| 取得 (取得成否) | `成功` / `失敗` / `404` など。失敗の行は確認済みにできない |
| 種類 / 備考 | 自由 (未確認の理由は備考に書く: 原典なし / 取得失敗 / リンク切れ / 食い違い / 旧制度 / 未施行 / 対象違い) |

`check.py ledger` が FAIL にすること:
- 確認済みなのに 出典URL・取得日・引用・適用時点 のどれかが無い / 取得が失敗。
- 確認済みの 主張 の数字・日付・率・金額が、引用か適用時点に同じ値で無い (漢数字は数字に直して比べる。「一日について八時間」は「8時間」と合う)。
- 確認済みの 引用 が、保存した原典の本文に同じ文字列で無い (下の §2.1)。
- 資料 (スライド本文・読み原稿・配布資料) の確認が要る語が、どの行の 主張・表記 にも無い。本人が言った数字も 区分=本人提供 で載せる。
- 未確認の行にしか当たらない語の場所に [要確認] が無い。

機械で拾う語 (`scripts/claims.py`):
- 日付: `2026年4月1日` / `令和8年4月1日` (西暦に直す) / `2026/4/1` / `4月1日` / `4月` / `2026年度` / `14:00`
- 金額: `1,163円` / `3.5万円` (= 35,000円) / `1億2,000万円`
- 率: `50%` / `50％` / `50パーセント` / `5割` (= 50%) / `2.5ポイント`。範囲 `10〜20%` は 2 語
- 数 + 単位: 人・名・件・社・日・か月・年・時間・分・回・倍・歳・週・枚 など
- 条番号: `第32条` / `第三十二条` / `第32条の2第1項`
- 単位の無い 3 桁以上の数・カンマ区切り・小数
- 法令名: 〜法・〜施行規則・〜施行令・〜条例・〜政令・〜省令・〜告示・〜通達 (「方法」「就業規則」などは除く)

機械で拾えないもの (検品で人が見る): 数字の無い主張 (「対象は中小企業のみ」)、文中の漢数字 (「八時間」は条番号の中だけ数字に直す)、主張の強さ (「できる」→「必ず」)、対象・条件の落とし、年や月だけの語の取り違え (同じ年・月の行なら通る)。

### 2.1 引用と原典の本文の照合

- 取得した原典の本文を、台帳の隣の `sources/` (生の本文は `sources/raw/`) に .txt / .md / .html で置く。PDF は `pdftotext` などで .txt にした物を置く。
- `check.py ledger` は台帳の隣に `sources/` があれば、確認済みの各行の引用 (「…」の中身。8 字以上) が、どれかの file に同じ文字列で有るかを見る。空白・改行・全角半角・〜 の違いは詰めて比べる。
- 別の場所なら `--sources <file かフォルダ>` (何度でも)。`sources/` が無い時は WARN (引用を原典と照らしていない) を出す。

## 3. 書き出し (scripts/build.py)

```
python3 scripts/build.py deck.html --out out [--formats pptx,pdf,notes] [--author "氏名"] [--notes notes.json] [--ledger ledger.md]
                         [--engine auto|chrome|python] [--unreviewed]
python3 scripts/build.py handout.html --out out --handout [--formats …]   # 配布物を同じ out/ と記録に足す（本体の後で）
```

| 出力 (out/) | 中身 |
|---|---|
| `<名前>.pptx` | 本文はテキストボックス、表は PowerPoint の表、読み原稿はノート。文書のプロパティの作成者・最終更新者は空 (`--author` で指定) |
| `<名前>.pdf` | Chrome の印刷。読み原稿は出ない。予備の書き出しでは、LibreOffice があれば pptx から作る (無ければ作らない) |
| `<名前>_読み原稿.md` | スライドごとの読み原稿 (字数と時間の目安の行は `<!-- ledger:skip -->`) |
| `manifest.json` | 書き出しの記録 (§5.2) |

- `--formats notes` だけなら Node.js・Chrome は要らない。
- `--engine auto` (既定): Chrome が見つからない・起動しない時は、Python だけの予備の書き出し (`html_to_pptx_static.py`) に自動で切り替え、理由を表示する。予備の書き出しは描画の確認ができていない書き出し (`adapters.md` §2.2)。`--engine chrome` は Chrome だけ (動かなければ止まる)、`--engine python` は予備だけ。
- PowerPoint・LibreOffice は Chrome より字幅を広く取るので、表の行が折り返して伸びることがある。`build.py` は表の行の高さを推定で先に取り、表の下の物 (出典の行など) を伸びた分だけ下げる (下の帯 = スライドの下 1 割から始まる物は動かさない)。下げきれない時は「注意:」を表示し、`check.py pptx` が FAIL にする。HTML の側でも、表の下に 1 行分の余白を残す。
- `--unreviewed`: 別文脈の検品ができずに渡す時。file 名が `<名前>_未検品.*` になり、pptx は各スライドの右上の「未検品」の箱と文書のプロパティ (題名・キーワード・分類)、PDF は各ページの右上に「未検品」が入る。読み原稿は `<名前>_読み原稿_未検品.md`。印の無い写しは作らない (`review.md` §どちらも使えない時)。
- `--handout`: 配布物 (配布 1 枚など) を本体の deck と同じ `out/` に書き出し、記録に「元の file」つきで足す。本体を先に書き出しておく。
- `--notes notes.json`: `["1枚目", "", "3枚目"]` か `{"1": "…", "3": "…"}`。HTML のノートより優先。
- 書き出したら必ず `python3 scripts/check.py pptx out/<名前>.pptx deck.html` (Chrome が使えない時は `check.py pptx` が自分で静的な比較に切り替え、WARN で知らせる。`--static` は付けない)。
- Codex では、`build.py` と Chrome を使う `check.py pptx` を囲い (sandbox) の外で実行する。囲いの中では Chrome が起動しない。手順と、許可が無い時 (予備の書き出しで渡し、「描画の確認ができていない書き出しです」と伝える) は `adapters.md` §2.1・§2.2。`build.py` の代わりに即席の変換器を書かない。`build.py` 以外で作った file は `check.py manifest` を通らず、納品しない。

## 4. 機械チェック (scripts/check.py)

どのサブコマンドも、行の頭が `FAIL` = 直す / `WARN` = 目で確かめる / `OK` = 合格の要約。終了コード 0 = 合格 (WARN だけなら 0)、1 = FAIL あり、2 = 使い方の誤り。

| command | 見ること |
|---|---|
| `check.py deck deck.html [--strict] [--phrases FILE]` | 部品集の版面の規約、タイトルの有無 (表紙・章扉以外)、書きかけ (TODO・◯◯・「ここに…を入れる」)、避ける言い回し (`scripts/data/banned_phrases.txt`、本文と読み原稿)。WARN: 話題の名前だけのタイトル、タイトルの語尾の混在、受給・加入を約束する言い方。`--strict` は WARN も FAIL にする |
| `check.py ledger ledger.md deck.html [ほかの成果物 …] [--sources DIR]` | §2。ほかの成果物 = `.html` (配布資料)・`.md`・`.txt`・`.docx`。旧形式 `ledger deck.html ledger.md` も読む |
| `check.py pptx out/<名前>.pptx deck.html [--static] [--overflow warn]` | 枚数、Chrome で描いた文字と pptx の文字の一致 (欠落 = FAIL。文字が画像になった枚もここで落ちる)、HTML の表が PowerPoint の表か、ノートが読み原稿と同じか、文書のプロパティが python-pptx の既定値でないか、はみ出しの推定 (箱の高さ・幅・表の下端・スライドの外 = FAIL)、表と下の物の重なり (行が折り返して伸びた時の推定を含む。PowerPoint・LibreOffice は表を下へ伸ばす = FAIL)。WARN: スライドの半分以上が画像。`--static` は Chrome を使わない (`<style>` の display:none・visibility:hidden は読むが、ほかの CSS で隠した文字を欠落と数えることがある) |
| `check.py pii <フォルダか file> [--allow FILE]…` | 人名 (敬称・「氏名:」・よくある名字+名)・電話・メール・郵便番号・住所・マイナンバーらしい 12 桁・人名の近くの健康の語・会社名+様/御中。表示は一部を伏せる。対象フォルダ直下の `pii-allowlist.txt` も自動で読む。`.` で始まる名前の file・フォルダは、対象の内側にあれば読まない |
| `check.py review-evidence review` | §5.1。揃わなければ `FAIL 未検品: <理由>` |
| `check.py manifest out review` | §5.2。渡す file が検品した版から書き出したものか |
| `check.py versions versions.md` | 版の記録の表で、どの行も見出しと同じ列の数か (FAIL)・状態が決まった語か (WARN)。形は `revision.md` §4 |

## 5. 検品の記録

### 5.1 独立の記録 (review/)

案件フォルダの `review/` に、巡ごとに次を置く (`<n>` = 1, 2, …)。

| file | 書く人 |
|---|---|
| `request-<n>.md` | 進行役 (依頼文。`review.md` の雛形) |
| `review-<n>.md` | reviewer (結果。`review.md` §結果の形) |
| `independence-<n>.json` | `scripts/review_record.py` (進行役は手で書かない) |
| `run-<n>.jsonl`・`run-<n>.stderr.log` | `review_record.py run` (別プロセスの出力) |

記録の取り方:

```
# subagent: 依頼文を書いた後、起動の直前と、返事が返った直後
python3 <skill>/scripts/review_record.py start  review --round <n> --method subagent
python3 <skill>/scripts/review_record.py finish review --round <n> --reviewer-id <返ってきた subagent の id> [--transcript <実行記録の file>]

# 別プロセス: 起動そのものを review_record.py にさせる (時刻・pid・終了コード・出力を script が取る)
python3 <skill>/scripts/review_record.py run review --round <n> --stdin review/request-<n>.md -- \
  codex exec --json --skip-git-repo-check -C . -s workspace-write -m gpt-6-astra -c model_reasoning_effort="high" -o review/last-<n>.md -
python3 <skill>/scripts/review_record.py run review --round <n> --stdin review/request-<n>.md -- \
  claude -p --output-format json --allowedTools "Read,Write,Bash(python3:*),WebFetch"
```

- `start` は `request-<n>.md` が無いと止まる。依頼文に `review.md` の雛形に無い行がある時も止まる (`<…>` を埋めた行だけを認める)。`run` も起動の前に同じことを確かめる。`review-<n>.md` が起動前からあっても止まる (前の結果を使い回さない)。同じ巡を起動し直す時は `--force`。
- 渡す物は案件フォルダの `BRIEF.md`・`ledger.md`・`deck.html` の 3 つに決まっている (別の名前なら `--brief` `--ledger` `--deck`)。配布物は `--extra <file>` (何度でも) で足し、依頼文に「配布物:」の行で書く。`start` の時点の sha256 を記録する。
- subagent は終了コードを返さない。`--exit` を付けなければ `exit_status: null` と、その理由 (`exit_note`) を記録する。これは「返事が返り、結果の file がある = 正常終了」として扱う決まり。

`independence-<n>.json` の項目 (schema `shiryo-kit/review-independence/v1`):

| 項目 | 中身 |
|---|---|
| `schema` `recorder` `round` | 形の名前・書いた script・何巡目 |
| `method` | `subagent` / `fresh-process` |
| `status` | `started` → `finished` (失敗時 `failed` / `no-result` / `launch-failed`) |
| `started_at` `ended_at` | script が時計から取った時刻 (ISO 8601、ミリ秒、時差つき) |
| `inputs` `inputs_sha256` | `{brief, ledger, deck}` の path (案件フォルダから) と sha256 |
| `request_file` `request_sha256` | 依頼文と、その起動時点の sha256 |
| `reviewer_id` | subagent の id / 別プロセスの会話 id (codex の `thread_id`、claude の `session_id`) か `pid:<番号>` |
| `exit_status` (`exit_note`) | 終了コード。subagent は null + 理由 |
| `pid` `command` `run_file` `run_sha256` | 別プロセスの時だけ |
| `transcript` `transcript_sha256` | subagent の実行記録を渡した時だけ |
| `result_file` `result_sha256` `result_mtime` | 結果の file と、終了時点の sha256・更新時刻 |

`check.py review-evidence review` は最後の巡について次を全部確かめる。1 つでも欠けたら `FAIL 未検品: <理由>`。
- 記録がある・schema と round が合う・method が 2 つのどちらか・status が finished。
- 起動 < 終了・未来の時刻でない。reviewer の識別子がある。reviewer の識別子が前の巡のどれとも違う (同じ reviewer に再検品を頼んでいない)。
- 別プロセス: 終了コード 0・pid がある・実行記録の file があり空でなく sha256 が同じ。subagent: 終了コード 0 か null (理由つき)。Codex の subagent でない (`start` の時に Codex の囲いの印の環境変数があった、または識別子が `/root/` で始まる → FAIL。Codex の subagent は会話を引き継がない起動を示せないため)。
- inputs がちょうど 3 つ・今の file の sha256 が記録と同じ (検品の後に直したら、その版は未検品)。配布物を `--extra` で渡した時は `extra_inputs` も同じ (今の file の sha256 が記録と同じで、依頼文にその file 名がある)。
- 依頼文が起動の後に書き換えられていない。
- 結果の file がある・sha256 が終了時点と同じ・更新時刻が起動〜終了 (+120 秒) の間・「結論: 合格」か「結論: 直しが必要」の行がある (雛形のままは FAIL)。
- WARN: 起動から終了まで 20 秒未満、結果に deck の sha256 が無い、spec_rev の行が無い、依頼文に 3 つの file 名が無い、前の巡の記録の不備。

これで分かること・分からないこと: script が時刻・pid・出力・file の sha256 を取るので、「起動していないのに検品したと書く」「検品の後に資料を直す」「結果を後から書き換える」は記録と合わなくなる。subagent が本当に作り手の会話を引き継いでいないかは記録からは分からない (起動の仕方は `review.md` の決まりに従う)。記録の JSON を手で偽造することは防げない。

### 5.2 書き出しの記録 (out/manifest.json) と照合

`build.py` が毎回 `out/manifest.json` を書く (schema `shiryo-kit/build-manifest/v1`):
`built_at`・`formats`・`deck` / `ledger` / `brief` (`{path (out からの相対), sha256}`、無ければ null)・`export_mode` (`chrome` / `python-fallback`)・`render_checked` (Chrome で描いたか)・`fallback_reason` (予備に切り替えた理由)・`unreviewed_mark` (`--unreviewed` の時)・`outputs` (`[{file, format, sha256, bytes, source, deck_sha256, mode, built_at}]`。`source` = 元の HTML (out からの相対)、`deck_sha256` = その HTML の sha256、`mode` = `chrome` / `python-fallback` / `libreoffice` / `text`)。元の file が変わっていない書き出しの行は残す (pptx の後で pdf、本体の後で配布物)。台帳は `--ledger` か、deck.html の隣の `ledger.md`。

`check.py manifest out review` が FAIL にすること:
- `manifest.json` が無い・読めない (→ `未検品`)。
- 書き出した後に deck.html が変わった。記録にある file が無い・書き出した後に変わった (手で直した pptx)・前の版の deck から書き出した。
- review-evidence が通らない (→ `未検品: …`)。
- 書き出した時の deck・台帳・BRIEF の sha256 が、最後の巡で検品した物と違う (→ `未検品: …`)。
- `out/` に、記録に無い pptx・pdf がある (`build.py` 以外で作った物。即席の変換器の出力など)。
- 配布物 (`source` が本体の deck でない行): 元の file が無い・書き出した後に変わった、または最後の巡の検品の `extra_inputs` に入っていない (→ `未検品: …`)。

通った時は `OK manifest: 状態=検品済み（…・書き出し=Chrome|予備（描画の確認なし）…）` か、結論が「直しが必要」なら `状態=検品済み・指摘が残っています` (+ WARN)。予備の書き出し (`export_mode: python-fallback`) は記録にあれば通り、WARN で「描画の確認ができていない書き出しです」と出る。`out/` にあって記録に無い md・docx・html は WARN (照合できないので渡さない)。

## 6. プレビュー (scripts/preview.py)

```
python3 scripts/preview.py <案件フォルダ>            # 裏で起動し、URL と PID を表示してすぐ戻る
python3 scripts/preview.py <案件フォルダ> --stop     # 止める
python3 scripts/preview.py <案件フォルダ> --port 9000 / --foreground (この画面で動かす。Ctrl+C で止める)
```

- 127.0.0.1 (このパソコン) だけで待ち受ける。直した HTML がすぐ見えるようにキャッシュさせない。
- 動いている間は `<案件フォルダ>/.shiryo-preview.json` (`{pid, port, url, dir, started_at}`) を書く。同じフォルダで 2 回起動しても 1 つだけ動く。`--stop` はその URL に問い合わせて同じ pid が答えた時だけ止める (pid の使い回しで別のプロセスを止めない)。

## 7. 必要な物と入れ方

| 物 | 要る command | macOS | Windows |
|---|---|---|---|
| Python 3.10 以上 | 全部 | 入っていなければ https://www.python.org/ | `winget install Python.Python.3.12` |
| python-pptx・lxml | build (pptx)・check pptx | `python3 -m venv ~/.shiryo-kit-venv && ~/.shiryo-kit-venv/bin/pip install python-pptx lxml` (以後 `~/.shiryo-kit-venv/bin/python3` で実行) | `py -m pip install python-pptx lxml` |
| LibreOffice (任意) | 予備の書き出しの PDF | 入っていれば自動で使う | 同左 |
| Node.js 22 以上 | build (pptx・pdf)・check pptx (Chrome で描く時。無ければ予備の書き出し・静的な比較に切り替わる) | `brew install node` | `winget install OpenJS.NodeJS.LTS` (入れた後はターミナルを開き直す) |
| Chrome (または Edge・Chromium・Brave) | 同上 | 通常の場所 (`/Applications`) にあれば自動で見つける | Edge は最初から入っている。自動で見つける |

環境変数: `CHROME_PATH` (または `SHIRYO_CHROME_PATH`) = ブラウザの場所を指定。`SHIRYO_CHROME_WAIT_MS` = ブラウザの起動を待つ時間 (既定 45000)。`SHIRYO_SOFFICE_TIMEOUT` = LibreOffice の時間の上限 (秒、既定 180)。python-pptx が無いと build (pptx) と check pptx は入れ方を表示して止まる。Node.js・Chrome が無い時は止まらず、build は予備の書き出しに、check pptx は静的な比較に切り替わる (`adapters.md` §2.2)。
deck / ledger / pii / review-evidence / manifest / preview / review_record は標準ライブラリだけで動く。
