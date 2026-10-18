"""check.py deck: 合格する例と、FAIL / WARN になる例（タイトル・書きかけ・避ける言い回し・読み原稿）。"""
import unittest

from _helpers import FIXTURES, TempDir, check, deck_html, fails, warns

GOOD1 = '<h1>就業規則は年1回見直すと揉めごとが減ります</h1><p>改正のたびに一行足すだけで防げます</p><aside class="notes"><p>今日の結論です。</p></aside>'
GOOD2 = '<h1>相談は早いほど費用が少なくて済みます</h1><p>小さいうちに直す</p><aside class="notes"><p>締めです。</p></aside>'


def run_deck(*slides, args=()):
    with TempDir() as d:
        p = d / "deck.html"
        p.write_text(deck_html(*slides), encoding="utf-8")
        return check("deck", p, *args)


class DeckCheck(unittest.TestCase):
    def test_clean_deck_passes(self):
        code, out, _ = run_deck(GOOD1, GOOD2)
        self.assertEqual(code, 0, out)
        self.assertIn("OK deck: 2 枚", out)
        self.assertEqual(fails(out), [])

    def test_sample_fixture_passes(self):
        code, out, _ = check("deck", FIXTURES / "sample_deck.html")
        self.assertEqual(code, 0, out)

    def test_missing_title_fails(self):
        code, out, _ = run_deck(GOOD1, "<p>タイトルの無いスライドの本文です</p>")
        self.assertEqual(code, 1)
        self.assertTrue(any("p2: タイトル" in f and "無い" in f for f in fails(out)), out)

    def test_cover_without_title_is_ok(self):
        cover = '<section class="s cover"><p>就業規則セミナー</p></section>'
        code, out, _ = run_deck(cover, GOOD1, GOOD2)
        self.assertFalse(any("p1: タイトル" in f for f in fails(out)), out)

    def test_todo_placeholder_fails(self):
        code, out, _ = run_deck(GOOD1, "<h1>手続きは3つで終わります</h1><p>TODO: 数字を入れる</p>")
        self.assertEqual(code, 1)
        self.assertTrue(any("書きかけ" in f and "TODO" in f for f in fails(out)), out)

    def test_marupo_placeholder_fails(self):
        code, out, _ = run_deck(GOOD1, "<h1>手続きは3つで終わります</h1><p>申請先は◯◯労働局です</p>")
        self.assertEqual(code, 1, out)

    def test_banned_phrase_fails_in_body(self):
        code, out, _ = run_deck(GOOD1, "<h1>手続きは3つで終わります</h1><p>まさに画期的な制度です</p>")
        self.assertEqual(code, 1)
        self.assertTrue(any("避ける言い回し" in f and "画期的" in f for f in fails(out)), out)

    def test_banned_phrase_checked_in_notes(self):
        s = '<h1>手続きは3つで終わります</h1><p>申請書を出す</p><aside class="notes"><p>まさに画期的です。</p></aside>'
        code, out, _ = run_deck(GOOD1, s)
        self.assertEqual(code, 1)
        self.assertTrue(any("読み原稿: 避ける言い回し" in f for f in fails(out)), out)

    def test_overpromise_warns(self):
        code, out, _ = run_deck(GOOD1, "<h1>助成金は申請できます</h1><p>この助成金は必ずもらえます</p>")
        self.assertTrue(any("必ずもらえ" in w for w in warns(out)), out)

    def test_polite_titles_allowed(self):
        # です・ます のタイトルは FAIL にしない（doctrine.md: そろえれば可）
        code, out, _ = run_deck(GOOD1, GOOD2)
        self.assertFalse(any("ですます" in ln for ln in out.splitlines()), out)

    def test_topic_only_title_and_mixed_endings_warn(self):
        code, out, _ = run_deck(GOOD1, "<h1>適用拡大の概要</h1><p>対象が広がる</p>")
        w = warns(out)
        self.assertTrue(any("話題の名前だけ" in x for x in w), out)
        self.assertTrue(any("語尾が混在" in x for x in w), out)

    def test_strict_turns_warn_into_fail(self):
        code, out, _ = run_deck(GOOD1, "<h1>適用拡大の概要</h1><p>対象が広がる</p>", args=("--strict",))
        self.assertEqual(code, 1, out)

    def test_no_slides_fails(self):
        with TempDir() as d:
            p = d / "x.html"
            p.write_text("<html><body><div>no slides</div></body></html>", encoding="utf-8")
            code, out, _ = check("deck", p)
        self.assertEqual(code, 1)
        self.assertIn("スライドが見つからない", out)


if __name__ == "__main__":
    unittest.main()
