"""読み原稿（patch (b)）: aside.notes / data-notes / 両方 / 無し、読み原稿 md、--notes json。"""
import json
import unittest

from _helpers import TempDir, deck_html, run, write_approved_brief
from deck_html import parse_deck


class Notes(unittest.TestCase):
    def test_parse_variants(self):
        d = parse_deck(deck_html(
            '<h1>一</h1><p>本文</p><aside class="notes"><p>段落1</p><p>段落2</p></aside>',
            '<section class="s" data-notes="属性の原稿"><h1>二</h1><p>本文</p></section>',
            '<section class="s" data-notes="先"><h1>三</h1><aside class="notes">後<br>改行</aside></section>',
            '<h1>四</h1><p>原稿なし</p>'))
        self.assertEqual([s.notes for s in d.slides], ["段落1\n段落2", "属性の原稿", "先\n後\n改行", ""])
        self.assertNotIn("段落1", d.slides[0].text)   # 読み原稿は本文に混ざらない

    def test_notes_markdown_and_json_override(self):
        with TempDir() as d:
            write_approved_brief(d)  # 関門 1 を通る BRIEF（書き出しの試験）
            (d / "deck.html").write_text(deck_html('<h1>結論です</h1><p>本文</p><aside class="notes"><p>HTML の原稿</p></aside>',
                                                   '<h1>次です</h1><p>本文</p>'), encoding="utf-8")
            code, out, err = run("build.py", "deck.html", "--out", "out", "--formats", "notes", cwd=d)
            self.assertEqual(code, 0, err)
            md = (d / "out" / "deck_読み原稿.md").read_text(encoding="utf-8")
            self.assertIn("## 1. 結論です", md)
            self.assertIn("HTML の原稿", md)
            self.assertIn("（読み原稿なし）", md)
            self.assertIn("<!-- ledger:skip -->", md)
            (d / "n.json").write_text(json.dumps({"2": "JSON の原稿"}, ensure_ascii=False), encoding="utf-8")
            code, out, err = run("build.py", "deck.html", "--out", "out", "--formats", "notes", "--notes", "n.json", cwd=d)
            md = (d / "out" / "deck_読み原稿.md").read_text(encoding="utf-8")
            self.assertIn("JSON の原稿", md)
            self.assertNotIn("HTML の原稿", md)


if __name__ == "__main__":
    unittest.main()
