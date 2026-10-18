"""check.py ledger: 台帳と全成果物の突き合わせ。合格・漏れ・[要確認] 抜け・確認済みの必須項目・引用との食い違い・原典の本文。"""
import unittest
import zipfile

from _helpers import FIXTURES, TempDir, check, deck_html, fails, warns

HEAD = "| ID | 主張 | 表記 | 区分 | 出典URL | 取得日 | 引用 | 適用時点 | 使用箇所 | 備考 |\n|---|---|---|---|---|---|---|---|---|---|\n"
URL = "https://laws.e-gov.go.jp/law/322AC0000000049"
Q32 = "使用者は、労働者に、休憩時間を除き一日について八時間を超えて、労働させてはならない。"


def row(i, claim, status, url="", date="", quote="", applies="", where="", forms="", memo=""):
    return f"| {i} | {claim} | {forms} | {status} | {url} | {date} | {quote} | {applies} | {where} | {memo} |\n"


CONFIRMED = row("L1", "法定労働時間は 1日8時間（労働基準法第32条）", "確認済み", URL, "2026-10-18", f"「{Q32}」",
                "現行（2026-10-18 時点で有効）", "p1")
UNCONFIRMED = row("L2", "月60時間超の割増率は 50%", "未確認", where="p1", memo="原典未取得")
SLIDE = "<h1>労働時間は1日8時間までです</h1><p>労働基準法第32条で決まっています</p>"


def run_ledger(ledger, *slides, extra=None, args=(), sources=None):
    with TempDir() as d:
        (d / "ledger.md").write_text("# 台帳\n\n" + HEAD + ledger, encoding="utf-8")
        (d / "deck.html").write_text(deck_html(*slides), encoding="utf-8")
        targets = ["deck.html"]
        for name, content in (extra or {}).items():
            p = d / name
            if isinstance(content, bytes):
                p.write_bytes(content)
            else:
                p.write_text(content, encoding="utf-8")
            targets.append(name)
        if sources is not None:
            (d / "sources" / "raw").mkdir(parents=True)
            (d / "sources" / "raw" / "S1.txt").write_text(sources, encoding="utf-8")
        return check("ledger", "ledger.md", *targets, *args, cwd=d)


def docx_bytes(paragraphs):
    import io
    body = "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in paragraphs)
    xml = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{body}</w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


class Ledger(unittest.TestCase):
    def test_sample_fixture_passes(self):
        code, out, _ = check("ledger", FIXTURES / "sample_ledger.md", FIXTURES / "sample_deck.html")
        self.assertEqual(code, 0, out)
        self.assertIn("OK ledger: 7 行", out)

    def test_old_cli_form_still_works(self):
        code, out, _ = check("ledger", FIXTURES / "sample_deck.html", FIXTURES / "sample_ledger.md")
        self.assertEqual(code, 0, out)

    def test_confirmed_with_kanji_quote_passes(self):
        code, out, _ = run_ledger(CONFIRMED, SLIDE)
        self.assertEqual(fails(out), [], out)
        self.assertEqual(code, 0)

    def test_number_missing_from_ledger_fails(self):
        code, out, _ = run_ledger(CONFIRMED, SLIDE, '<h1>参加費は3,000円です</h1><p>当日払い</p>')
        self.assertEqual(code, 1)
        self.assertTrue(any("3,000円" in f and "台帳に無い" in f for f in fails(out)), out)

    def test_number_in_notes_is_checked(self):
        s = SLIDE + '<aside class="notes"><p>受付は15:30からです。</p></aside>'
        code, out, _ = run_ledger(CONFIRMED, s)
        self.assertTrue(any("読み原稿" in f and "15:30" in f for f in fails(out)), out)

    def test_unconfirmed_needs_mark(self):
        code, out, _ = run_ledger(CONFIRMED + UNCONFIRMED, SLIDE + "<p>割増率は50%になります</p>")
        self.assertEqual(code, 1)
        self.assertTrue(any("50%" in f and "[要確認] が無い" in f for f in fails(out)), out)
        for mark in ("[要確認]", "【要確認】", "［要確認］"):
            code, out, _ = run_ledger(CONFIRMED + UNCONFIRMED, SLIDE + f"<p>割増率は50%になります{mark}</p>")
            self.assertEqual(code, 0, f"{mark}: {out}")

    def test_confirmed_requires_fields(self):
        cases = {
            "出典URL": row("L1", "1日8時間", "確認済み", "", "2026-10-18", f"「{Q32}」", "現行"),
            "取得日": row("L1", "1日8時間", "確認済み", URL, "", f"「{Q32}」", "現行"),
            "引用": row("L1", "1日8時間", "確認済み", URL, "2026-10-18", "", "現行"),
            "適用時点": row("L1", "1日8時間", "確認済み", URL, "2026-10-18", f"「{Q32}」", ""),
        }
        for field, r in cases.items():
            code, out, _ = run_ledger(r, "<h1>労働時間は1日8時間までです</h1><p>原則</p>")
            self.assertEqual(code, 1, field)
            self.assertTrue(any(field in f for f in fails(out)), f"{field}: {out}")

    def test_quote_number_mismatch_fails(self):
        r = row("L1", "法定労働時間は 1日10時間", "確認済み", URL, "2026-10-18", f"「{Q32}」", "現行", "p1")
        code, out, _ = run_ledger(r, "<h1>労働時間は1日10時間までです</h1><p>原則</p>")
        self.assertEqual(code, 1)
        self.assertTrue(any("10時間" in f and "引用・適用時点に見当たらない" in f for f in fails(out)), out)

    def test_fetch_failed_cannot_be_confirmed(self):
        r = ("| ID | 主張 | 区分 | 出典URL | 取得日 | 引用 | 適用時点 | 取得 |\n|---|---|---|---|---|---|---|---|\n"
             f"| L1 | 1日8時間 | 確認済み | {URL} | 2026-10-18 | 「{Q32}」 | 現行 | 失敗 (404) |\n")
        with TempDir() as d:
            (d / "ledger.md").write_text(r, encoding="utf-8")
            (d / "deck.html").write_text(deck_html("<h1>労働時間は1日8時間までです</h1><p>原則</p>"), encoding="utf-8")
            code, out, _ = check("ledger", "ledger.md", "deck.html", cwd=d)
        self.assertEqual(code, 1)
        self.assertTrue(any("取得が" in f for f in fails(out)), out)

    def test_unknown_status_and_duplicate_id(self):
        r = row("L1", "1日8時間", "たぶん確認") + row("L1", "50%", "未確認")
        code, out, _ = run_ledger(r, "<h1>結論です</h1><p>本文</p>")
        self.assertTrue(any("区分「たぶん確認」が不明" in f for f in fails(out)), out)
        self.assertTrue(any("ID が重複" in f for f in fails(out)), out)

    def test_no_table_fails(self):
        with TempDir() as d:
            (d / "ledger.md").write_text("# 台帳\n表がまだ無い\n", encoding="utf-8")
            (d / "deck.html").write_text(deck_html("<h1>結論です</h1><p>本文</p>"), encoding="utf-8")
            code, out, _ = check("ledger", "ledger.md", "deck.html", cwd=d)
        self.assertEqual(code, 1)
        self.assertIn("表が見つからない", out)

    def test_markdown_and_docx_deliverables(self):
        md = "# 読み原稿\n\n労働時間は1日8時間です。\n\n参加者は120人を見込みます。\n<!-- ledger:skip --> 読み原稿 900 字\n"
        code, out, _ = run_ledger(CONFIRMED, SLIDE, extra={"原稿.md": md, "配布資料.docx": docx_bytes(["助成額は上限72万円です。"])})
        f = fails(out)
        self.assertTrue(any("原稿.md:5" in x and "120人" in x for x in f), out)
        self.assertTrue(any("配布資料.docx" in x and "72万円" in x for x in f), out)
        self.assertFalse(any("900" in x for x in f), out)   # ledger:skip の行は見ない

    def test_skip_classes_and_data_attribute(self):
        s = SLIDE + '<div class="foot">2026年11月20日時点 p.12</div><p data-ledger="skip">No.1234</p>'
        code, out, _ = run_ledger(CONFIRMED, s)
        self.assertEqual(fails(out), [], out)

    def test_page_narrowing_with_s_prefix(self):
        # 同じ値の行が 2 つ: 未確認（p2 用）と本人提供（p1 用）。p1 は本人提供に絞られ [要確認] 不要
        r = row("L1", "定員は120人", "本人提供", where="s1 本文") + row("L2", "全国で120人", "未確認", where="s2 本文")
        code, out, _ = run_ledger(r, "<h1>定員は120人です</h1><p>先着順</p>", "<h1>全国で120人が受講しました</h1><p>昨年度</p>")
        f = fails(out)
        self.assertFalse(any("p1" in x for x in f), out)
        self.assertTrue(any("p2" in x and "[要確認] が無い" in x for x in f), out)

    def test_traps_ledger_columns_are_read(self):
        # review-traps の台帳（資料での書き方・取得した本文の該当箇所 (引用)・確認日）を表として読める
        from _helpers import TRAPS
        code, out, _ = check("ledger", TRAPS / "ledger.md", TRAPS / "deck.html")
        self.assertNotIn("表が見つからない", out)
        self.assertNotIn("区分", "".join(f for f in fails(out) if "不明" in f))

    # --- 引用と保存した原典の本文
    def test_quote_found_in_sources_passes(self):
        code, out, _ = run_ledger(CONFIRMED, SLIDE, sources=f"第三十二条\n{Q32}\n")
        self.assertEqual(code, 0, out)
        self.assertIn("原典の本文 1 file", out)

    def test_quote_whitespace_and_width_insensitive(self):
        src = Q32.replace("、", "、\n  ")
        code, out, _ = run_ledger(CONFIRMED, SLIDE, sources=src)
        self.assertEqual(code, 0, out)
        from ledger import _norm_quote
        self.assertEqual(_norm_quote("週の所定労働時間が２０時間以上（３６〜５０人）"), _norm_quote("週の所定労働時間が20時間以上(36～50人)"))

    def test_altered_quote_fails_against_sources(self):
        src = Q32.replace("八時間", "十時間")
        code, out, _ = run_ledger(CONFIRMED, SLIDE, sources=src)
        self.assertEqual(code, 1)
        self.assertTrue(any("sources/" in f and "見つからない" in f for f in fails(out)), out)

    def test_no_sources_warns(self):
        code, out, _ = run_ledger(CONFIRMED, SLIDE)
        self.assertTrue(any("原典の本文と照らしていない" in w for w in warns(out)), out)

    def test_explicit_sources_missing_fails(self):
        code, out, _ = run_ledger(CONFIRMED, SLIDE, args=("--sources", "nowhere"))
        self.assertEqual(code, 1)
        self.assertIn("--sources が見つからない", out)

    # --- CC1-6: 和暦の日付が 2 つある引用で止まらない・読み原稿の data-ledger="skip"
    def test_quote_with_two_wareki_dates_does_not_stop(self):
        q = "「この法律は、平成三十一年四月一日から施行する。ただし、第二条の規定は、令和二年四月一日から施行する。」"
        r = row("L1", "取得させる決まりは2019年4月1日から", "確認済み", URL, "2026-10-19", q, "2019年4月1日施行", "p1")
        code, out, err = run_ledger(r, "<h1>2019年4月1日から始まりました</h1><p>本文</p>")
        self.assertNotIn("Traceback", err)
        self.assertEqual(fails(out), [], out + err)
        self.assertEqual(code, 0, out + err)

    def test_two_dates_on_one_slide_line(self):
        r = row("L1", "2019年4月1日に施行", "本人提供", where="p1") + row("L2", "2020年4月1日に中小企業へ", "本人提供", where="p1")
        code, out, err = run_ledger(r, "<h1>2019年4月1日に始まり、2020年4月1日に中小企業にも広がりました</h1><p>本文</p>")
        self.assertNotIn("Traceback", err)
        self.assertEqual(fails(out), [], out + err)

    def test_skip_marker_in_notes(self):
        notes = ('<aside class="notes"><p data-ledger="skip">たとえば架空の会社で、10日付いた人が3日取ったとします。</p>'
                 '<p>労働時間は1日8時間です。<span data-ledger="skip">（例: 9時から18時）</span></p></aside>')
        code, out, _ = run_ledger(CONFIRMED, SLIDE + notes)
        self.assertEqual(fails(out), [], out)
        self.assertEqual(code, 0, out)

    def test_notes_without_skip_still_checked(self):
        notes = '<aside class="notes"><p data-ledger="skip">架空の例: 10日のうち3日</p><p>参加者は120人です。</p></aside>'
        code, out, _ = run_ledger(CONFIRMED, SLIDE + notes)
        f = fails(out)
        self.assertTrue(any("読み原稿" in x and "120人" in x for x in f), out)
        self.assertFalse(any("10日" in x or "3日" in x for x in f), out)


if __name__ == "__main__":
    unittest.main()
