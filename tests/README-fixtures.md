# tests/README-fixtures.md — 試験用 fixture の索引と使い方

対象: shiryo-kit の受け入れ試験 (REQUIREMENTS spec_rev 1.0 §6) のうち AC-02 / 03 / 04 / 05 / 07 / 08 / 10 / 11 の素材。
作成: U5a、2026-10-18。**データはすべて架空** (事務所・人名・住所・電話 090-0000-xxxx / 050-0000-xxxx / 03-0000-xxxx・メールは example.com)。制度の事実だけは実在の官庁資料に基づく (取得日・URL・引用は `claims-test/claims-key.md` §0)。

## 1. 最重要の運用ルール: 正解 file を作り手に見せない

| 作り手 (試験される skill を動かす agent) に渡してよい | 渡してはいけない (評価者・user actor 専用) |
|---|---|
| `fixtures/past-materials/` (フォルダごと) | `fixtures/answer-keys/` (全部) |
| `fixtures/claims-test/request/` (`依頼文.md`、任意で `brief-preanswers.md`) | `fixtures/claims-test/claims-key.md` |
| `fixtures/review-traps/` の `deck.html` `BRIEF.md` `ledger.md` `source-snapshot.md` (reviewer に) | `fixtures/personas/*.md` の評価者用の節、`fixtures/_build/` |
| `fixtures/personas/seeded-memory/` (メモリーの初期状態として) | |

- `fixtures/claims-test/` はフォルダごと渡さない (key が同じフォルダにある)。`request/` だけ渡す。
- `fixtures/personas/*.md` は `===ACTOR===` 〜 `===END ACTOR===` の間だけ user actor agent に渡す。actor は作り手と別文脈・別プロセスで動かす。
- 実行記録 (モデル・環境・起動した別 agent の ID/コマンド・使った seeded-memory の版) は評価のたびに残す。AC-07 は自己申告でなく起動記録で判定する。

## 2. 一覧

| 場所 | 中身 | 主に使う AC | 正解 |
|---|---|---|---|
| `fixtures/past-materials/` | 架空の一人社労士 (柏木 遼 / つきがおか労務オフィス) の過去資料 4 本: `2025-09_36kyotei-seminar.pptx` (python-pptx 製・8 枚・表 1・ノート付き)、`2026-03_newsletter.docx` (python-docx 製)、`2025-10_36kyotei-checksheet.pdf` (LibreOffice 変換)、`2025-09_speaking-memo.md`。口調の癖 12 個と個人情報の罠 12 個入り | AC-05 (R-07/11/P8)、AC-02/03 の入力 | `fixtures/answer-keys/past-materials-key.md` |
| `fixtures/claims-test/request/` | 試験依頼 `依頼文.md` (テーマ: パート・アルバイトの社会保険の適用拡大、使う日 2026-11-20、スライド + 読み原稿 + 図) と、ヒアリングを省く時の `brief-preanswers.md` | AC-04 (R-06)、persona-a の初回依頼 | `fixtures/claims-test/claims-key.md` |
| `fixtures/claims-test/claims-key.md` | 台帳に載るべき主張 10 + 追加 7、AC-04 の 6 つの罠 (確かめられない / リンク切れ / 数字の食い違い / 旧制度 / 公布済み未施行 / 対象違い) と正しい振る舞い、原典 S1〜S7 (URL・取得日・逐語引用) | AC-04、AC-08 | (これ自体が key) |
| `fixtures/personas/a-first-time.md` | 初回の本人役。隠れた事実 12 と開示条件、承認直前の訂正、判定表 | AC-02、AC-05 | 同 file の評価者用の節 |
| `fixtures/personas/b-second-deck.md` | 同じ本人の 2 回目 (別の回: 南支部・年休)。推奨答・今回だけの上書き・訂正・削除の試験 | AC-03 | 同上 |
| `fixtures/personas/c-other-client.md` | 別の顧問先 (サンプル製作所)。案件限定情報の持ち越し禁止・数え方の対象違い (42 名と 33 名) | AC-03 後半、AC-04 副次 | 同上 |
| `fixtures/personas/d-out-of-template.md` | 型に無い依頼 (顧問先の新入社員研修の配布資料 A4 4 ページ・白黒)。労働基準法第39条の引用つき | AC-10、AC-07 の通し | 同上 |
| `fixtures/personas/seeded-memory/` | persona-b / c を単独で走らせる初期メモリー (`before-b/` `before-c/`)。形式は仮 (UND-04) | AC-03 | `seeded-memory/README.md` |
| `fixtures/review-traps/` | 5 枚の小デッキ `deck.html` + `BRIEF.md` + `ledger.md` + 原典抜粋 `source-snapshot.md`。誤引用 1 + 数字の不一致 1 + 台帳漏れ 1 + 要件違反 5 | AC-07 (R-08/P5)、AC-08 の素材 | `fixtures/answer-keys/review-traps-key.md` |
| `fixtures/answer-keys/` | past-materials と review-traps の正解 | — | — |
| `fixtures/_build/build_past_materials.py` | past-materials の pptx / docx / pdf の再生成スクリプト (`python3 -I build_past_materials.py <出力先>`。python-pptx・python-docx・soffice が要る) | — | — |

## 3. AC ごとの使い方

### AC-02 初回ヒアリング (R-03/04)
1. 作り手に `persona-a` の依頼文 (= `claims-test/request/依頼文.md`) を渡す。メモリーは空。過去資料フォルダの場所は聞かれた時だけ渡す。
2. 別 agent が `persona-a` の actor 節で本人役を演じる (開示条件を守らせる)。
3. 評価者は a-first-time.md 末尾の判定表で、止める項目の確定時刻・BRIEF の承認記録・訂正の追記 (45 分 + 質疑 15 分)・途中質問の分類を見る。

### AC-03 メモリー (R-05/P8)
1. a の実走後のメモリー (または `seeded-memory/before-b/`) で `persona-b` を走らせる。質問数 (同じ項目をゼロから聞いた回数) を a と比べる。推奨答・「今回だけ」・訂正・削除・保存前の確認を判定表で見る。
2. b の実走後 (または `before-c/`) で `persona-c` を走らせる。本部・南支部の案件限定情報が出ないこと (grep 語は c の判定表)、削除した「家計簿」が戻らないこと。
- 注意: 過去資料には「家計簿」のたとえが残っている。c で過去資料を読み直して再抽出する agent は、削除指示済みの癖を除外する必要がある (除外した記録があれば合格)。

### AC-04 出典台帳 (R-06)
1. 作り手に `claims-test/request/依頼文.md` だけを渡して完走させる (ヒアリングを省く時は `brief-preanswers.md` を加える)。
2. 評価者は成果物 (スライド・原稿・図) から主張を抜き、`claims-key.md` §2 C の手順で漏れ 0 を判定、E-01〜E-10 と 6 つの罠を照合、「確認済み」の引用の有無を見る。
3. 実走が遅れた場合は S1〜S7 を取り直し、変わっていれば key_version を上げる (特に S1/S2 の 2027 年 9 月/10 月の記載、リンク切れ URL が 404 のままか)。

### AC-05 口調・個人情報 (R-07/11/P8)
1. 作り手に `past-materials/` を読ませて、口調の抽出 (出典 file つき) と完成資料を出させる。
2. 別 agent が過去資料と完成資料を並べて `past-materials-key.md` §1 の V-01〜V-12 で判定 (抽出と反映)。
3. 保存されたメモリーと完成資料に対し、§2-3 の grep と目視を実行 (個人情報 0 件)。

### AC-07 検品 (R-08/P5)
1. `review-traps/` の 4 file を、作り手と別の文脈で起動した reviewer に渡す (取得手段があれば使わせる。無ければ `source-snapshot.md`)。
2. `review-traps-key.md` で 8 つの欠陥の検出・誤検出・実行記録を判定。別文脈が使えない設定で「未検品」になるかは別試験。

### AC-08 修正と再検品 (P7)
- `claims-test` の完成資料、または `review-traps/deck.html` に対して「軽減特例は 5 年と書いてあるが 3 年では」と修正依頼 (M-2) を出し、出典確認 (台帳更新) → 再検品 → 納品版と検品済み版の対応記録、を確かめる。専用 fixture は作っていない (上の素材で足りると判断)。

### AC-10 型 4 種と型に無い依頼
- `persona-d` を走らせる。判定表 (型のプレビュー・成果物の形・白黒・法定と社内ルールの区別・最後まで通る)。

### AC-11 チャット版の代用テスト
- 専用 fixture は作っていない。`persona-a` の actor 節 + `claims-test/request/依頼文.md` を、道具なしのモデル (チャット版の指示文だけを与えたモデル) に与えて代用できる。ヒアリング → 骨子 → 原稿 → 出典一覧 (要確認つき) → メモカードの順に出ること、独立検品済みと名乗らないことは、`claims-key.md` §3 の罠 (T1〜T6) と personas の判定表の「チャット版でも出るべき項目」を流用して判定する。**この項目は評価者が組み替えて使う前提 (未整備)**。

## 4. 確かめたこと / 確かめていないこと (2026-10-18)

確かめた (実行して確認):
- past-materials: pptx を python-pptx で読み戻し (8 枚・ノート付き・表あり)、docx を python-docx で読み戻し、PDF を pdftotext で本文抽出できること。個人情報の配置 (P-01〜P-12) は抽出テキストを grep して key と一致。
- claims-test: S1〜S3 は curl で HTML 本文化し引用を逐語一致で確認、S4〜S6 は PDF を pdftotext で本文抽出して引用、S5 の通知は公布日・施行日を本文で確認、S7 は e-Gov API v2 で現行版 (20261001) の本文を取得。リンク切れ URL は curl で HTTP 404、実在 URL は 200。
- review-traps: `deck.html` が skill の `scripts/deck_html.py` で 5 スライド・タイトル・ノートとして読めること。
- personas/d: e-Gov API で労働基準法第39条 (版 20260717、現行) の本文を取得し引用。

確かめていない (正直に):
- claims-key の e-Gov 条文照合は、企業規模要件 36 人以上 (令和9年10月1日) を定める条文の位置を特定していない。根拠は所管官庁 (S1/S2/S6) の説明のみ。
- 令和7年法律第74号の公布日は S5 (官庁の通知本文) による。官報は見ていない。
- 「約200万人」「約7割」に当たる公的数字は探していない (罠の設計)。
- pptx のレンダリング: pptx を LibreOffice で描画して見た目を確かめていない (fixtures は読み取り用で、AC-06 の対象ではない)。docx → PDF の変換結果は本文抽出のみ確認。
- `skill/shiryo-kit/references/html-contract.md` は作成時点で存在しなかった。review-traps の HTML と台帳の形式は暫定 (欠陥の内容は形式に依存しない)。契約確定後にタグ・列だけ合わせる。
- AC-11 / AC-12 / AC-13 の専用 fixture は無い。
- 試験依頼の期待区分は 2026-10-18 時点の制度。時間が経てば施行日・ページ内容が変わりうる (key_version で管理)。
