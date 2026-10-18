"""pii.py / check.py pii: 見つけるべき物・見つけてはいけない物・許可リスト。"""
import unittest

from _helpers import TempDir, check, fails
from pii import scan_text

POSITIVE = {
    "phone": "連絡先 090-0000-1234 まで",
    "email": "taro@example.com に送る",
    "postal": "〒100-0001",
    "address": "東京都千代田区千代田1-1 に住む",
    "mynumber": "番号 1234 5678 9012",
    "org": "サンプル製作所 様 の案件",
}
NAMES = ["田中様から相談", "佐藤さんの件", "氏名: 鈴木一郎", "山田太郎が担当"]
NEGATIVE = ["皆様へのお知らせ", "お客様の声", "同様の手続き", "仕様の変更", "ご担当者様", "社長さんに確認", "先生方へ",
            "パートさんの所定労働時間", "賃金の額に関係なく対象", "障害年金の制度の説明",
            # 出典の URL の中の数字は電話番号・マイナンバーではない (RT-CC-3: e-Gov の法令番号を電話と誤認)
            "出典: https://laws.e-gov.go.jp/law/322AC0000000049 (原典の確認日 2026年10月18日)",
            "https://www.mhlw.go.jp/content/000123456789.pdf", "法令番号 322AC0000000049"]
# URL を外しても、URL の外・tel: の電話番号は拾い続ける
PHONE_STILL = ["電話0312345678", "TEL:03-1234-5678", "tel:0312345678", "詳しくは https://example.com/a 090-0000-1234 まで",
               # URL の後に空白なしで和文が続いても、その先の電話番号は拾う (URL を和文まで伸ばさない)
               "（https://example.com、電話03-1234-5678）", "詳細はhttps://example.com/infoまたは電話0312345678へ",
               "https://example.com/お問い合わせ。TEL03-1234-5678", "www.example.jpの担当090-1234-5678",
               "受付3F03-1234-5678"]


class Pii(unittest.TestCase):
    def test_positive_kinds(self):
        for kind, text in POSITIVE.items():
            found = [k for _, k, _ in scan_text(text)]
            self.assertIn(kind, found, f"{kind}: {text} → {found}")

    def test_names(self):
        for text in NAMES:
            self.assertIn("name", [k for _, k, _ in scan_text(text)], text)

    def test_health_near_name(self):
        found = [k for _, k, _ in scan_text("田中様は適応障害で通院中")]
        self.assertIn("health", found)

    def test_negatives_not_flagged(self):
        for text in NEGATIVE:
            self.assertEqual(scan_text(text), [], text)

    def test_phone_outside_url_still_found(self):
        for text in PHONE_STILL:
            self.assertIn("phone", [k for _, k, _ in scan_text(text)], text)

    def test_allowlist(self):
        self.assertEqual(scan_text("柏木様の事務所", allow=["柏木"]), [])
        self.assertTrue(scan_text("柏木様の事務所"))

    def test_cli_fails_and_masks(self):
        with TempDir() as d:
            (d / "memo.md").write_text("担当: 田中様 090-0000-1234\n", encoding="utf-8")
            code, out, _ = check("pii", d)
        self.assertEqual(code, 1)
        self.assertTrue(fails(out))
        self.assertNotIn("090-0000-1234", out)   # 表示は伏せる
        self.assertNotIn("田中様", out)

    def test_cli_allowlist_file_and_clean_pass(self):
        with TempDir() as d:
            (d / "memo.md").write_text("話し手は柏木様。口調は です・ます。\n", encoding="utf-8")
            (d / "pii-allowlist.txt").write_text("# 本人\n柏木\n", encoding="utf-8")
            code, out, _ = check("pii", d)
        self.assertEqual(code, 0, out)

    def test_dot_dir_target_is_scanned(self):
        # SKILL.md: 案を 資料メモ/.保存前/ に書いて check.py pii 資料メモ/.保存前 を通す
        with TempDir() as d:
            draft = d / "資料メモ" / ".保存前"
            draft.mkdir(parents=True)
            (draft / "案.md").write_text("佐藤さんは休職中\n", encoding="utf-8")
            code, out, _ = check("pii", draft)
        self.assertEqual(code, 1, out)


if __name__ == "__main__":
    unittest.main()
