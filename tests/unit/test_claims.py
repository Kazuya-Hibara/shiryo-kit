"""claims.py: 確認が要る語の拾い方と正規形。"""
import unittest

from _helpers import SCRIPTS  # noqa: F401  (sys.path)
from claims import extract, kanji_numerals_to_digits


def kinds(text):
    return [(t.kind, t.raw) for t in extract(text)]


class Claims(unittest.TestCase):
    def test_wareki_equals_seireki(self):
        a = [t for t in extract("令和8年4月1日") if t.kind == "date"][0]
        b = [t for t in extract("2026年4月1日") if t.kind == "date"][0]
        self.assertTrue(a.matches(b))

    def test_man_yen_value(self):
        a = [t for t in extract("3.5万円") if t.kind == "yen"][0]
        b = [t for t in extract("35,000円") if t.kind == "yen"][0]
        self.assertTrue(a.matches(b))
        c = [t for t in extract("8.8万円") if t.kind == "yen"][0]
        self.assertFalse(a.matches(c))

    def test_wari_is_percent(self):
        a = [t for t in extract("5割") if t.kind == "pct"][0]
        b = [t for t in extract("50%") if t.kind == "pct"][0]
        self.assertTrue(a.matches(b))

    def test_kanji_article(self):
        a = [t for t in extract("労働基準法第三十二条") if t.kind == "art"][0]
        b = [t for t in extract("第32条") if t.kind == "art"][0]
        self.assertTrue(a.matches(b))

    def test_range_gives_two_tokens(self):
        pct = [t for t in extract("10〜20%") if t.kind == "pct"]
        self.assertEqual(len(pct), 2, kinds("10〜20%"))

    def test_law_names_and_not_law(self):
        laws = [r for k, r in kinds("労働基準法と育児・介護休業法の方法") if k == "law"]
        self.assertTrue(any("労働基準法" in x for x in laws), laws)
        self.assertFalse(any(x.endswith("方法") for x in laws), laws)
        self.assertEqual([r for k, r in kinds("就業規則の作成方法") if k == "law"], [])

    def test_small_unitless_numbers_ignored(self):
        self.assertEqual(extract("論点は 3 つ、12 番"), [])

    def test_quantity_units(self):
        k = kinds("従業員51人以上、週20時間、3か月")
        self.assertIn(("qty", "51人"), k)
        self.assertTrue(any(r.startswith("20時間") for _, r in k), k)
        self.assertTrue(any(r.startswith("3か月") for _, r in k), k)

    def test_kanji_numerals_converted(self):
        self.assertIn("8時間", kanji_numerals_to_digits("一日について八時間"))


if __name__ == "__main__":
    unittest.main()
