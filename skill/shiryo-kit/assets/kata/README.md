# assets/kata/ — 型 (かた) 4 種

資料の骨格の見本。ヒアリング (`references/hearing.md` §型の見せ方) で本人にプレビューを見せて選んでもらい、下書き (P4) で部品から組む。見た目は部品 (`assets/parts/`) の流用で、作り込んでいない。

| id | 名前 | 使う場面 | 枚数の目安 | 話す/配る | 既定の配色 |
|---|---|---|---|---|---|
| `seminar` | セミナー | 講演・登壇で投影して話す | 12-16 | 話す (文字を大きく、説明は読み原稿へ) | warm |
| `advisory` | 顧問先説明 | 顧問先の経営者・人事担当へ制度・規程変更を説明 | 8-12 | 両方 (配る寄り) | navy |
| `proposal` | 提案 | 見込み客へのサービス・契約の提案 | 9-13 | 両方 (配る寄り) | navy |
| `report` | 報告 | 顧問先への定期報告・診断結果 | 7-12 | 配る | mono |

各型のフォルダ: `<id>/sample.html` (架空の事務所「みなと社労士事務所」の見本。事実・数字はすべて架空、制度の根拠は `[要確認]`) と `<id>/preview.png` (全スライドの一覧画像)。

## kata.json の読み方

`kata.json` が正。型ごとに次を持つ。

- `when` / `fits` / `audience` — いつ使うか。型の推奨理由を言うときの材料
- `slides` — 枚数の目安 (typical / min / max)
- `mode` / `density` / `density_note` — 話す資料か配る資料か。`density` は `kata.json` 先頭の `density` の名前 (`read` = 部品の既定、`talk` = 文字を約 1.3 倍)
- `tone` / `flow` — 口調と話の順。`doctrine.md` の判断軸と同じ向き (型はその実例)
- `parts` — `new_deck.py --parts` にそのまま渡せる部品 ID 列
- `sequence` — 1 枚ごとの `part` / `role` (表紙・結論・背景・制度の説明・比較・手順・事例・まとめ・連絡先 …) / `example_title` (結論型タイトルの例。型どおりに写さない)
- `default_skin` / `skins` — 配色。値は先頭の `skins` に CSS 変数で入っている (warm = 部品の既定の茶、navy = 紺、mono = 墨色)
- `notes_required` — 読み原稿 (`<aside class="notes">`) を必ず書くか。`seminar` は true

## ヒアリングでの使い方

1. 場面 (話す/配る・時間・人数) と受け手が決まったら、`mode` と `when` が合う型を 1 つ推奨する (理由は `fits` から 1 行)。
2. 本人に `<id>/preview.png` を見せる。ブラウザで開けるなら `python3 scripts/preview.py <assets/kata>` の URL、できなければファイルを直接開いてもらう。見られない環境では `kata.json` の `when` と `flow` を 2 行ずつ言葉で示す。
3. 配色は `skins` から 2〜3 つを `label` で示し、既定でよいか 1 問で聞く (`preview.png` は既定の配色)。
4. 選ばれた型は事務所共通メモの「型の好み」の候補にする (保存は P8 で本人に見せてから)。

## 下書きでの使い方

1. 型の `parts` で骨組みを作る: `python3 scripts/new_deck.py --parts <parts> --title "<資料名>" -o deck.html`
2. `sequence` の `role` を見ながら、各枚の文言を書く。部品の見本文 (`Text 1`、`ラベル 1`、`YYYY` など) は残さない (`check.py deck` が FAIL にする)。タイトルは結論型の 1 文 (`doctrine.md` §3)。`sample.html` に同じ部品で書いた例がある。
3. 骨子の段階では、枚を足す・消す・並べ替えるのはモデルが判断してよい。`sequence` は既定で、固定ではない。足す枚は同じ部品を使う (部品の見分け方は `scripts/new_deck.py --list`)。
4. 配色と文字の大きさ: `kata.json` の `skins.<名前>.css_vars` を `:root{...}` として、`density.talk.css` はそのまま、生成した HTML の最初の `</style>` の直前に追記する (どちらも `sample.html` の末尾の `<style>` に入っている形)。
5. 読み原稿は `notes_required` が true の型は必ず、他の型も話す場面があれば書く (`doctrine.md` §8)。
6. 納品前の検査は通常どおり (`check.py deck` → `build.py` → `check.py pptx`)。

## 型に無い依頼 (例: 社内研修の配布資料、助成金の案内、採用説明会)

型を無理に当てはめない。

1. 近い型を 1 つ選ぶ (研修の配布資料なら `advisory` の流れ + `seminar` の章立て、など)。`flow` と `mode` が近いものを選ぶ。
2. 「この型を土台に、ここを変えます」と言葉で示し、了承をもらう (`hearing.md` §型の見せ方)。
3. 変える場合も、部品は `new_deck.py --list` の中から選び、`sequence` の役割 (表紙・結論・背景・…・連絡先) を満たしているかだけ確かめる。型にない役割 (例: 演習・ワーク) は、表 (b09) かカード (b08) で作る。
4. どの型にも寄せられないときは、部品から直接組んでよい。型は出発点であって、制約ではない。

## 新しい型を足す

1. `new_deck.py --list` から部品を選び、1 本のデッキを作る。話の順は `doctrine.md` §4 の表 (受け手の状態) で決める。
2. 部品の見本文をすべて自分の文言に置き換える (架空の事務所名・架空の数字。制度や数字の根拠が要る所は `[要確認]`)。`check.py deck` が FAIL 0 になること。
3. `<新id>/sample.html` に保存。配色と文字の大きさは上の手順 4 のとおり。
4. プレビュー画像を作る: `python3 scripts/build.py <sample.html> --out <作業フォルダ> --formats pdf` で PDF を作り、`pdftoppm -r 55 -png` でページごとの PNG にして、番号つきで並べて 1 枚にする (ImageMagick の `montage` でもよい)。自分の目で全ページを見て、はみ出しがないか確かめる。
5. `python3 scripts/build.py <sample.html> --out <作業フォルダ>` の後に `python3 scripts/check.py pptx <出力>.pptx <sample.html>` が OK になること。
6. `kata.json` の `kata` に 1 件足す (`id` / `name` / `when` / `fits` / `audience` / `slides` / `mode` / `density` / `tone` / `flow` / `default_skin` / `skins` / `parts` / `sequence` / `sample` / `preview`)。この README の表も更新する。

## 部品の選び方についての注意 (既知の問題)

サンプルは基本パーツ集 (`b01`〜`b27`) だけで組んでいる。追加パーツ集の `m01`〜`m35` は現状では使えない。

- `new_deck.py` が追加パーツ集の `:root` (余白・版面の変数) を壊す。`assets/parts/freeform_parts_more_16x9.html` の冒頭コメントに `<style>` という文字列があり、`split_css` がそこから CSS を切り出すため。m 系の枚だけ余白が 0 になり、PDF では紙面の左上に縮んで出る。
- `html_to_pptx.py` が CSS の `zoom: 0.8` を文字サイズに反映しない。m 系の枚は pptx で文字が約 1.25 倍になり、`check.py pptx` が「箱の幅を超えそう」と FAIL する。

両方が直るまで、`kata.json` の `optional_parts` にある ID (m01 m10 m12 m21 m22 m26 m35) は追加しない。直ったら、同じ役割の枚 (結論・比較・リスク・まとめ) をそちらに差し替えられる。

## 出どころ

部品の HTML は `assets/parts/` (carnot-tech/consulting-pptx-skill, MIT。リポジトリ直下の `NOTICE` を参照) の流用。配色 navy は部品ファイル内のコメントにある cool スキンの値、warm は部品の既定、mono は同じ変数名で作った灰色の組。文言・構成は shiryo-kit の自作 (他の公開テンプレートからの複製なし)。
