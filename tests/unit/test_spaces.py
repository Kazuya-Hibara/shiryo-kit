"""空白の規則（patch (a)）: 作者の空白・全角空白・&nbsp; は残し、和文の間のソース改行だけ詰める。静的な読み取りと Chrome の描画の両方。"""
import tempfile
import unittest
from pathlib import Path

from _helpers import HAS_CHROME, deck_html
from deck_html import parse_deck

SLIDE = ("<h1>中小企業向け 就業規則\n見直し</h1><p>経営者向け　第2回</p><p>A&nbsp;B</p>"
         "<p>就業<span>\n規則</span>の見直し</p><p>Hello\nworld</p><p>改正は\n  2026年4月</p>")


def check_texts(test, texts):
    test.assertIn("中小企業向け 就業規則見直し", texts)        # 作者の半角空白は残す・和文の間の改行は詰める
    test.assertIn("経営者向け　第2回", texts)              # 全角空白は残す
    test.assertTrue(any(t in texts for t in ("A B", "A B")), texts)  # &nbsp; は空白として残す
    test.assertIn("就業規則の見直し", texts)                    # インライン要素の境目の改行も詰める
    test.assertIn("Hello world", texts)                        # 欧文の間の改行は空白 1 つ
    test.assertIn("改正は 2026年4月", texts)                    # 和文と数字の間の改行は空白 1 つ（詰めない）


class StaticSpaces(unittest.TestCase):
    def test_static_reader(self):
        d = parse_deck(deck_html(SLIDE))
        texts = [b.text for b in d.slides[0].blocks]
        check_texts(self, texts)
        self.assertEqual(d.slides[0].title, "中小企業向け 就業規則見直し")


@unittest.skipUnless(HAS_CHROME, "Node.js 22+ と Chrome が要る")
class RenderedSpaces(unittest.TestCase):
    def test_chrome_dump_matches(self):
        from html_to_pptx import run_dump
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "d.html"
            p.write_text(deck_html(SLIDE), encoding="utf-8")
            data = run_dump(p, td, text_only=True)
        texts = [t for t in data["slides"][0]["text"].split("\n") if t.strip()]
        check_texts(self, texts)


if __name__ == "__main__":
    unittest.main()
