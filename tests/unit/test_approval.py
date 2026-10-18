"""F4 2a: 関門 1 の機械の関門（approval.py・build.py・new_deck.py・check.py approval）。良い BRIEF と悪い BRIEF。"""
import unittest

from _helpers import TempDir, check, run, write_approved_brief

DECK = "<html><body><section class='s'><h1>題は結論を言う</h1><p>本文</p></section></body></html>"

HEAD = "---\nspec_rev: {rev}\nstatus: {status}\n案件: 試験\n---\n\n# BRIEF — 試験\n\n"


def brief(status="承認済み", rev=1, shown=("1",), approval="- 2026-10-19 10:00 本人「この内容で。」 (要約 rev 1 への返事。spec_rev 1)"):
    s = HEAD.format(rev=rev, status=status)
    s += "## 要約の提示\n" + "".join(f"- 2026-10-19 09:{i:02d} 要約 rev {r} を見せた\n" for i, r in enumerate(shown)) + "\n"
    s += "## 承認記録\n" + (approval + "\n" if approval else "") + "\n## 1. 要件\n"
    return s


BAD = {
    "unapproved": brief(status="下書き", rev=0, approval=""),
    "no_summary_log": brief(shown=()),
    "conditional": brief(shown=("1",), approval="- 2026-10-19 10:00 本人「2点違います。開始は13時30分です。そこを直したら、"
                                                 "それで進めてください。」 (要約 rev 1 への返事。spec_rev 1)"),
    "fix_then_go": brief(shown=("1",), approval="- 2026-10-19 10:00 本人「時間は60分ではなく45分。直して進めて」 (要約 rev 1 への返事。spec_rev 1)"),
    "older_rev": brief(shown=("1", "2"), approval="- 2026-10-19 10:00 本人「この内容で。」 (要約 rev 1 への返事。spec_rev 1)"),
    "no_rev_named": brief(approval="- 2026-10-19 10:00 本人「この内容で。」 (spec_rev 1)"),
    "status_says_request": brief(status="依頼に基づき制作"),
}

def said(words, rev=1, shown=("1",)):
    return brief(shown=shown, approval=f"- 2026-10-19 10:00 本人「{words}」 (要約 rev {rev} への返事。spec_rev 1)")


# 点検 (F4 2a) で見つかった言い方。条件つき・直しを含む返事は止める
BAD_WORDS = ["タイトルは『見直し』に。そこを直したら進めて", "『45分』に直したら、それで進めてください", "そこだけ修正でお願いします",
             "開始は13時30分にしておいてください。それで作ってください", "13時30分にして進めてください",
             "時間を45分に変更してお願いします", "空欄の管理簿にしてください。それで進めて", "質疑を15分足して、それで進めて",
             "時間だけ45分に修正のうえ進めてください", "1点だけ、時間は45分です。他はOKです、進めてください",
             "直しておいて。作っていいです", "45分に直して、あとはお任せします", "会場ではなくオンラインで進めて",
             "訂正した条件での明示的な作成指示"]
GOOD_WORDS = ["この内容で。", "はい、これで大丈夫です", "OKです、お願いします", "直す所はありません", "変更なしで進めて",
              "この内容であれば進めてください", "問題なければ進めてください", "これでよければ進めてください",
              "よければこのままお願いします", "急ぎじゃなくていいので、この内容でお願いします", "はい、この内容で作ってください。",
              "この条件で進めてください", "この条件で作ってください", "間違っていません、この内容で", "間違ってないです",
              "このままにしてください", "当日を楽しみにしています", "参考にしてもらった資料で大丈夫です", "希望どおりにしてくれて",
              "質問は1点だけです", "これだけです", "入れてくれてありがとう"]

GOOD = {
    "plain": brief(),
    "after_correction": brief(shown=("1", "2"), approval="- 2026-10-19 10:30 本人「はい、この内容で作ってください。」 (要約 rev 2 への返事。spec_rev 1)"),
    "no_changes_needed": brief(approval="- 2026-10-19 10:00 本人「直す所はありません。この内容で進めてください」 (要約 rev 1 への返事。spec_rev 1)"),
}


class Approval(unittest.TestCase):
    def test_module_bad_and_good(self):
        from approval import problems
        with TempDir() as d:
            for name, text in BAD.items():
                (d / "BRIEF.md").write_text(text, encoding="utf-8")
                self.assertTrue(problems(d / "BRIEF.md")[0], f"bad の {name} が通ってしまった")
            for name, text in GOOD.items():
                (d / "BRIEF.md").write_text(text, encoding="utf-8")
                self.assertEqual(problems(d / "BRIEF.md")[0], [], f"good の {name} が止められた")
            (d / "BRIEF.md").unlink()
            self.assertTrue(problems(d / "BRIEF.md")[0])

    def test_words(self):
        from approval import problems
        with TempDir() as d:
            for w in BAD_WORDS:
                (d / "BRIEF.md").write_text(said(w), encoding="utf-8")
                self.assertTrue(problems(d / "BRIEF.md")[0], f"条件つきが通った: {w}")
            for w in GOOD_WORDS:
                (d / "BRIEF.md").write_text(said(w), encoding="utf-8")
                self.assertEqual(problems(d / "BRIEF.md")[0], [], f"本物の承認が止められた: {w}")

    def test_back_half_of_a_correction_and_time_order(self):
        """訂正と同じ返事の後ろ半分だけを承認と書いた形・提示より前の時刻の承認は止める。書式の揺れ（BOM・引用符・### 見出し）は読む。"""
        from approval import problems
        log = ("\n## 11. 決定ログ\n| 日時 | 種類 | 内容 | 本人の言葉 | spec_rev |\n|---|---|---|---|---|\n"
               "| 10:00 | 変更 | 時間 | 「1点違います。時間は45分です。そこを直したら、それで進めてください。」 | 0 |\n")
        with TempDir() as d:
            (d / "BRIEF.md").write_text(said("それで進めてください。", rev=2, shown=("1", "2")) + log, encoding="utf-8")
            self.assertTrue(problems(d / "BRIEF.md")[0])
            early = brief(shown=("1",), approval="- 2026-10-19 08:00 本人「この内容で。」 (要約 rev 1 への返事。spec_rev 1)")
            (d / "BRIEF.md").write_text(early, encoding="utf-8")
            self.assertEqual([k for k, _ in problems(d / "BRIEF.md")[0]], ["early"])
            after = brief() + ("\n## 11. 決定ログ\n| 日時 | 種類 | 内容 | 本人の言葉 | spec_rev |\n|---|---|---|---|---|\n"
                               "| 2026-10-20 14:00 | 変更 | 表紙の日付 | 「表紙の日付を直して、あとはこの内容でいいです」 | 2 |\n")
            (d / "BRIEF.md").write_text(after, encoding="utf-8")
            self.assertEqual(problems(d / "BRIEF.md")[0], [], "承認の後の直し (P7) で止まった")
            sub = brief().replace("## 承認記録\n", "## 承認記録\n### 初回\n")
            (d / "BRIEF.md").write_text(sub, encoding="utf-8")
            self.assertEqual(problems(d / "BRIEF.md")[0], [], "小見出しで節が切れた")
            loose = "\ufeff" + brief().replace("status: 承認済み", 'status: "承認済み"').replace("## 要約の提示", "### 要約の提示")
            (d / "BRIEF.md").write_text(loose, encoding="utf-8")
            self.assertEqual(problems(d / "BRIEF.md")[0], [])

    def test_message_says_the_right_next_step(self):
        from approval import gate
        with TempDir() as d:
            (d / "BRIEF.md").write_text(brief(status="下書き", rev=0, approval=""), encoding="utf-8")
            m = gate(d / "BRIEF.md")
            self.assertIn("要約 rev 1 への本人の返事を待つ", m)
            self.assertNotIn("直しを反映した要約", m)
            (d / "BRIEF.md").write_text(brief(status="下書き", rev=0), encoding="utf-8")
            self.assertIn("status を承認済み・spec_rev を 1 に直して", gate(d / "BRIEF.md"))
            (d / "BRIEF.md").write_text(said("そこを直したら進めて"), encoding="utf-8")
            self.assertIn("rev 2", gate(d / "BRIEF.md"))
            self.assertIn("--brief", gate(d / "nothing" / "BRIEF.md"))

    def test_brief_option_reads_another_place(self):
        with TempDir() as d:
            (d / "sub").mkdir()
            (d / "sub" / "deck.html").write_text(DECK, encoding="utf-8")
            write_approved_brief(d)
            self.assertEqual(run("build.py", "sub/deck.html", "--out", "out", "--formats", "notes", cwd=d)[0], 2)
            code, out, err = run("build.py", "sub/deck.html", "--out", "out", "--formats", "notes", "--brief", "BRIEF.md", cwd=d)
            self.assertEqual(code, 0, out + err)

    def test_build_refuses_and_says_what_to_do(self):
        with TempDir() as d:
            (d / "deck.html").write_text(DECK, encoding="utf-8")
            for name in ("conditional", "older_rev"):
                (d / "BRIEF.md").write_text(BAD[name], encoding="utf-8")
                code, out, err = run("build.py", "deck.html", "--out", "out", "--formats", "notes", cwd=d)
                self.assertEqual(code, 2, name)
                self.assertIn("関門 1", err)
                self.assertIn("要約 rev 2", err)  # 条件つき → 直した rev 2 を見せる / 古い版 → 最後に見せた rev 2 に聞く
                self.assertIn("再承認ではありません", err)
                self.assertFalse((d / "out").exists() and any((d / "out").iterdir()), f"{name}: 止めたのに書き出した")
            (d / "BRIEF.md").unlink()
            code, out, err = run("build.py", "deck.html", "--out", "out", "--formats", "notes", cwd=d)
            self.assertEqual(code, 2)
            self.assertIn("BRIEF.md がありません", err)
            write_approved_brief(d)
            code, out, err = run("build.py", "deck.html", "--out", "out", "--formats", "notes", cwd=d)
            self.assertEqual(code, 0, out + err)

    def test_new_deck_refuses_without_approval(self):
        with TempDir() as d:
            code, out, err = run("new_deck.py", "--parts", "b01,b10", "-o", d / "deck.html")
            self.assertEqual(code, 2)
            self.assertFalse((d / "deck.html").exists())
            (d / "BRIEF.md").write_text(BAD["fix_then_go"], encoding="utf-8")
            self.assertEqual(run("new_deck.py", "--parts", "b01,b10", "-o", d / "deck.html")[0], 2)
            write_approved_brief(d)
            code, out, err = run("new_deck.py", "--parts", "b01,b10", "-o", d / "deck.html")
            self.assertEqual(code, 0, out + err)
            self.assertTrue((d / "deck.html").exists())
            self.assertEqual(run("new_deck.py", "--list")[0], 0)  # 一覧を見るだけなら止めない

    def test_check_approval_command(self):
        with TempDir() as d:
            (d / "BRIEF.md").write_text(BAD["unapproved"], encoding="utf-8")
            code, out, _ = check("approval", d / "BRIEF.md")
            self.assertEqual(code, 1)
            self.assertIn("FAIL", out)
            self.assertNotIn("('", out)
            self.assertIn("rev 1 への本人の返事を待つ", out)
            write_approved_brief(d)
            code, out, _ = check("approval", d / "BRIEF.md")
            self.assertEqual(code, 0, out)

    def test_template_example_passes(self):
        """brief-template.md の雛形（承認済みの例）がそのまま関門を通る。"""
        import re
        from _helpers import SCRIPTS
        from approval import problems
        t = (SCRIPTS.parent / "references" / "brief-template.md").read_text(encoding="utf-8")
        body = re.search(r"```markdown\n(.*?)```", t, flags=re.S).group(1)
        with TempDir() as d:
            (d / "BRIEF.md").write_text(body, encoding="utf-8")
            self.assertEqual(problems(d / "BRIEF.md")[0], [])


if __name__ == "__main__":
    unittest.main()
