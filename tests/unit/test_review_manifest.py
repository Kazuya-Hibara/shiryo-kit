"""review_record.py + check.py review-evidence / manifest（AC-07・AC-08）と preview.py の起動・停止。"""
import hashlib
import json
import re
import sys
import time
import unittest

from _helpers import SCRIPTS, TRAPS, TempDir, check, fails, run, warns


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def filled_request(n=1, extra=""):
    """references/review.md の雛形の <…> を埋めただけの依頼文（extra は雛形に無い行）。"""
    doc = (SCRIPTS.parent / "references" / "review.md").read_text(encoding="utf-8")
    body = re.search(r"## reviewer への依頼文.*?```markdown\n(.*?)\n```", doc, re.S).group(1)
    body = "\n".join(ln for ln in body.splitlines() if "<配布物の HTML>" not in ln)  # 配布物が無い時は行を消す
    for k, v in (("<案件フォルダ>", "/work/資料/case"), ("<skill>", "/skills/shiryo-kit"), ("<案件>", "テストの案件"),
                 ("<n>", str(n)), ("<名前>", "deck"), (" <ほかの成果物>", ""), ("<BRIEF の spec_rev をそのまま>", "1")):
        body = body.replace(k, v)
    return body + ("\n" + extra + "\n" if extra else "\n")


def reviewer_cmd(verdict="合格", deck_sha="", sleep=0.0, code=0, write=True):
    body = f"# 検品結果\\n## 結論: {verdict}\\n- deck.html sha256: {deck_sha}\\nspec_rev: 1\\n"
    return [sys.executable, "-c",
            "import sys,json,time;sys.stdin.read();print(json.dumps({'type':'thread.started','thread_id':'t-1'}));"
            f"time.sleep({sleep});" + (f"open('review/review-1.md','w',encoding='utf-8').write('{body}');" if write else "")
            + f"sys.exit({code})"]


class Case:
    def __init__(self, d):
        self.d = d
        for n in ("BRIEF.md", "ledger.md", "deck.html"):
            (d / n).write_bytes((TRAPS / n).read_bytes())
        (d / "review").mkdir()
        (d / "review" / "request-1.md").write_text(filled_request(1), encoding="utf-8")

    def rec(self, *args, env=None):
        return run("review_record.py", *args, cwd=self.d, env=env)

    def fresh(self, **kw):
        return self.rec("run", "review", "--round", "1", "--stdin", "review/request-1.md", "--",
                        *reviewer_cmd(deck_sha=sha(self.d / "deck.html"), **kw))

    def evidence(self):
        return check("review-evidence", "review", cwd=self.d)


class ReviewEvidence(unittest.TestCase):
    def test_missing_evidence_is_unreviewed(self):
        with TempDir() as d:
            c = Case(d)
            code, out, _ = c.evidence()
        self.assertEqual(code, 1)
        self.assertTrue(all(f.startswith("FAIL 未検品:") for f in fails(out)), out)

    def test_no_review_dir_is_unreviewed(self):
        with TempDir() as d:
            code, out, _ = check("review-evidence", d / "review")
        self.assertEqual(code, 1)
        self.assertIn("未検品", out)

    def test_fresh_process_record_passes(self):
        with TempDir() as d:
            c = Case(d)
            code, out, err = c.fresh()
            self.assertEqual(code, 0, err)
            rec = json.loads((d / "review" / "independence-1.json").read_text(encoding="utf-8"))
            self.assertEqual(rec["method"], "fresh-process")
            self.assertEqual(rec["reviewer_id"], "t-1")
            self.assertIsInstance(rec["pid"], int)
            self.assertEqual(rec["exit_status"], 0)
            self.assertEqual(set(rec["inputs"]), {"brief", "ledger", "deck"})
            code, out, _ = c.evidence()
        self.assertEqual(code, 0, out)
        self.assertIn("結論=合格", out)
        self.assertTrue(any("短すぎる" in w for w in warns(out)), out)

    def test_nonzero_exit_is_unreviewed(self):
        with TempDir() as d:
            c = Case(d)
            code, _, _ = c.fresh(code=3)
            self.assertNotEqual(code, 0)
            code, out, _ = c.evidence()
        self.assertEqual(code, 1)
        self.assertIn("未検品", out)

    def test_reviewer_wrote_nothing_is_unreviewed(self):
        with TempDir() as d:
            c = Case(d)
            code, _, err = c.fresh(write=False)
            self.assertNotEqual(code, 0)
            self.assertIn("結果", err)
            code, out, _ = c.evidence()
        self.assertEqual(code, 1)

    def test_deck_changed_after_review_is_unreviewed(self):
        with TempDir() as d:
            c = Case(d)
            c.fresh()
            with open(d / "deck.html", "a", encoding="utf-8") as f:
                f.write("<!-- 直した -->")
            code, out, _ = c.evidence()
        self.assertEqual(code, 1)
        self.assertTrue(any("検品の後に deck.html が変わった" in f for f in fails(out)), out)

    def test_result_edited_after_review_is_unreviewed(self):
        with TempDir() as d:
            c = Case(d)
            c.fresh()
            with open(d / "review" / "review-1.md", "a", encoding="utf-8") as f:
                f.write("追記\n")
            code, out, _ = c.evidence()
        self.assertEqual(code, 1)
        self.assertTrue(any("書き換えられた" in f for f in fails(out)), out)

    def test_hand_written_record_without_run_log_fails(self):
        # 作り手の自己申告（手書きの JSON・実行記録なし）は通らない
        with TempDir() as d:
            c = Case(d)
            (d / "review" / "review-1.md").write_text("## 結論: 合格\nspec_rev: 1\n", encoding="utf-8")
            rec = {"schema": "shiryo-kit/review-independence/v1", "round": 1, "method": "fresh-process", "status": "finished",
                   "started_at": "2026-10-18T10:00:00+09:00", "ended_at": "2026-10-18T10:05:00+09:00", "reviewer_id": "me",
                   "exit_status": 0, "inputs": {"brief": "BRIEF.md", "ledger": "ledger.md", "deck": "deck.html"},
                   "inputs_sha256": {k: sha(d / n) for k, n in (("brief", "BRIEF.md"), ("ledger", "ledger.md"), ("deck", "deck.html"))}}
            (d / "review" / "independence-1.json").write_text(json.dumps(rec), encoding="utf-8")
            code, out, _ = c.evidence()
        self.assertEqual(code, 1)
        f = "\n".join(fails(out))
        self.assertIn("pid", f)
        self.assertIn("実行記録", f)

    def test_extra_inputs_rejected(self):
        with TempDir() as d:
            c = Case(d)
            c.fresh()
            p = d / "review" / "independence-1.json"
            rec = json.loads(p.read_text(encoding="utf-8"))
            rec["inputs"]["notes"] = "作り手のメモ.md"
            p.write_text(json.dumps(rec), encoding="utf-8")
            code, out, _ = c.evidence()
        self.assertEqual(code, 1)
        self.assertIn("3 つでない", out)

    def test_subagent_start_finish(self):
        with TempDir() as d:
            c = Case(d)
            code, _, err = c.rec("start", "review", "--round", "1", "--method", "subagent")
            self.assertEqual(code, 0, err)
            # 起動前からある結果は使い回させない（start の後に書かれた物だけ）
            (d / "review" / "review-1.md").write_text(f"## 結論: 直しが必要\n- deck.html sha256: {sha(d / 'deck.html')}\nspec_rev: 1\n",
                                                     encoding="utf-8")
            code, _, err = c.rec("finish", "review", "--round", "1", "--reviewer-id", "agent-abc")
            self.assertEqual(code, 0, err)
            rec = json.loads((d / "review" / "independence-1.json").read_text(encoding="utf-8"))
            self.assertIsNone(rec["exit_status"])
            self.assertTrue(rec["exit_note"])
            code, out, _ = c.evidence()
        self.assertEqual(code, 0, out)
        self.assertIn("結論=直しが必要", out)

    def test_start_refuses_stale_result(self):
        with TempDir() as d:
            c = Case(d)
            (d / "review" / "review-1.md").write_text("## 結論: 合格\n", encoding="utf-8")
            code, _, err = c.rec("start", "review", "--round", "1")
        self.assertNotEqual(code, 0)
        self.assertIn("起動の前からある", err)

    def test_template_verdict_fails(self):
        with TempDir() as d:
            c = Case(d)
            c.rec("start", "review", "--round", "1")
            (d / "review" / "review-1.md").write_text("## 結論: 合格 / 直しが必要\n", encoding="utf-8")
            c.rec("finish", "review", "--round", "1", "--reviewer-id", "a")
            code, out, _ = c.evidence()
        self.assertEqual(code, 1)
        self.assertIn("雛形のまま", out)


    def _subagent_round(self, c, n, reviewer_id, env=None):
        d = c.d
        (d / "review" / f"request-{n}.md").write_text(filled_request(n), encoding="utf-8")
        code, _, err = c.rec("start", "review", "--round", str(n), env=env)
        self.assertEqual(code, 0, err)
        (d / "review" / f"review-{n}.md").write_text(f"## 結論: 合格\n- deck.html sha256: {sha(d / 'deck.html')}\nspec_rev: 1\n",
                                                   encoding="utf-8")
        code, _, err = c.rec("finish", "review", "--round", str(n), "--reviewer-id", reviewer_id)
        self.assertEqual(code, 0, err)

    def test_same_reviewer_for_next_round_fails(self):
        # CX-7: 再検品で前の巡と同じ reviewer に続きを頼んだら FAIL（WARN ではない）
        with TempDir() as d:
            c = Case(d)
            self._subagent_round(c, 1, "agent-1")
            self._subagent_round(c, 2, "agent-1")
            code, out, _ = c.evidence()
        self.assertEqual(code, 1, out)
        self.assertTrue(any("1 巡目と同じ" in f for f in fails(out)), out)

    def test_new_reviewer_for_next_round_passes(self):
        with TempDir() as d:
            c = Case(d)
            self._subagent_round(c, 1, "agent-1")
            self._subagent_round(c, 2, "agent-2")
            code, out, _ = c.evidence()
        self.assertEqual(code, 0, out)
        self.assertIn("2 巡目", out)

    def test_request_off_template_is_refused(self):
        # CX-8: 作り手の観点（「特に…を検品」「目安10分」）が依頼文に入っていたら start が止まる
        for leak in ("特に日付・人数・経過措置を重点的に検品してください。", "今回の修正: 5年→3年", "目安10分で終えてください。"):
            with TempDir() as d:
                c = Case(d)
                (d / "review" / "request-1.md").write_text(filled_request(1, leak), encoding="utf-8")
                code, _, err = c.rec("start", "review", "--round", "1")
                self.assertNotEqual(code, 0, leak)
                self.assertIn("雛形", err)
                self.assertIn(leak, err)
                self.assertFalse((d / "review" / "independence-1.json").exists())
                # run（別プロセス）でも起動の前に止まる
                code, _, err = c.fresh()
                self.assertNotEqual(code, 0, leak)
                self.assertFalse((d / "review" / "run-1.jsonl").exists())

    def test_codex_subagent_is_unreviewed(self):
        # CX-2: Codex の subagent は会話を引き継がない起動を示せない → 記録が揃っていても未検品
        for env, rid in (({"CODEX_SANDBOX": "seatbelt"}, "agent-1"), (None, "/root/review_seminar")):
            with TempDir() as d:
                c = Case(d)
                self._subagent_round(c, 1, rid, env=env)
                code, out, _ = c.evidence()
            self.assertEqual(code, 1, out)
            self.assertTrue(any("Codex の subagent" in f for f in fails(out)), out)

    def _start_with(self, text):
        with TempDir() as d:
            c = Case(d)
            (d / "review" / "request-1.md").write_text(text, encoding="utf-8")
            return c.rec("start", "review", "--round", "1")

    def test_request_leak_inside_placeholder_is_refused(self):
        # 埋め字の後ろ・中に作り手の観点を足す / 埋め字を埋め忘れる
        base = filled_request(1)
        led = next(l for l in base.splitlines() if "check.py ledger" in l)
        for text in (base.replace(led, led + " （特に日付・人数・経過措置を重点的に検品）"),
                     base.replace("spec_rev: 1", "spec_rev: 1 今回の修正: 5年→3年"),
                     base.replace("テストの案件", "A社。特に日付を重点的に検品してください"),
                     base.replace("最後の 1 行: spec_rev: 1", "最後の 1 行: spec_rev: <BRIEF の spec_rev をそのまま>")):
            code, _, err = self._start_with(text)
            self.assertNotEqual(code, 0, text)
            self.assertIn("雛形", err)

    def test_request_valid_variants_pass(self):
        # Windows の path、pptx が無い時に行を消す、ほかの成果物を足す
        base = filled_request(1)
        led = next(l for l in base.splitlines() if "check.py ledger" in l)
        nopptx = "\n".join(l for l in base.splitlines() if "check.py pptx" not in l).replace("・out/ の file", "")
        for text in (base.replace("/work/資料/case", r"C:\Users\k\資料\case").replace("/skills/shiryo-kit", r"C:\Users\k\.agents\skills\shiryo-kit"),
                     nopptx,
                     base.replace(led, led + " /work/資料/case/配布資料.html /work/資料/case/out/deck_読み原稿.md")):
            code, _, err = self._start_with(text)
            self.assertEqual(code, 0, err)

    def test_request_template_filled_passes(self):
        with TempDir() as d:
            c = Case(d)
            code, _, err = c.rec("start", "review", "--round", "1")
        self.assertEqual(code, 0, err)


class Manifest(unittest.TestCase):
    def build(self, d):
        return run("build.py", "deck.html", "--out", "out", "--formats", "notes", cwd=d)

    def test_reviewed_build_passes_and_changes_fail(self):
        with TempDir() as d:
            c = Case(d)
            self.assertEqual(self.build(d)[0], 0)
            m = json.loads((d / "out" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(m["deck"]["sha256"], sha(d / "deck.html"))
            self.assertEqual(m["ledger"]["sha256"], sha(d / "ledger.md"))
            self.assertEqual([o["file"] for o in m["outputs"]], ["deck_読み原稿.md"])
            c.fresh()
            code, out, _ = check("manifest", "out", "review", cwd=d)
            self.assertEqual(code, 0, out)
            self.assertIn("状態=検品済み", out)
            # 書き出した file を手で直した
            with open(d / "out" / "deck_読み原稿.md", "a", encoding="utf-8") as f:
                f.write("足した\n")
            code, out, _ = check("manifest", "out", "review", cwd=d)
            self.assertEqual(code, 1)
            self.assertTrue(any("書き出した後に変わった" in f for f in fails(out)), out)

    def test_unlisted_pptx_in_out_fails(self):
        # CX-1: build.py の記録に無い pptx（即席の変換器の出力）が out/ にあれば渡さない
        with TempDir() as d:
            c = Case(d)
            self.build(d)
            c.fresh()
            (d / "out" / "deck.pptx").write_bytes(b"PK\x03\x04 not from build.py")
            code, out, _ = check("manifest", "out", "review", cwd=d)
        self.assertEqual(code, 1, out)
        self.assertTrue(any("build.py の書き出しの記録に無い" in f for f in fails(out)), out)

    def test_rebuilt_from_edited_deck_is_unreviewed(self):
        # 検品の後に数字を直して書き出し直した（AC-08: 直したら検品に戻る）
        with TempDir() as d:
            c = Case(d)
            self.build(d)
            c.fresh()
            p = d / "deck.html"
            p.write_text(p.read_text(encoding="utf-8").replace("最大5年間", "3年間"), encoding="utf-8")
            self.build(d)
            code, out, _ = check("manifest", "out", "review", cwd=d)
        self.assertEqual(code, 1)
        self.assertTrue(any(f.startswith("FAIL 未検品") for f in fails(out)), out)

    def test_no_manifest_or_no_review(self):
        with TempDir() as d:
            Case(d)
            (d / "out").mkdir()
            code, out, _ = check("manifest", "out", "review", cwd=d)
            self.assertEqual(code, 1)
            self.assertIn("未検品", out)
            self.build(d)
            code, out, _ = check("manifest", "out", "review", cwd=d)
        self.assertEqual(code, 1)
        self.assertIn("未検品", out)

    def test_findings_left_state(self):
        with TempDir() as d:
            c = Case(d)
            self.build(d)
            c.fresh(verdict="直しが必要")
            code, out, _ = check("manifest", "out", "review", cwd=d)
        self.assertEqual(code, 0, out)
        self.assertIn("検品済み・指摘が残っています", out)


class Preview(unittest.TestCase):
    def test_start_reuse_stop(self):
        import urllib.request
        with TempDir() as d:
            (d / "deck.html").write_text("<html><body>x</body></html>", encoding="utf-8")
            code, out, err = run("preview.py", d, "--port", "8811", timeout=60)
            try:
                self.assertEqual(code, 0, err)
                info = json.loads((d / ".shiryo-preview.json").read_text(encoding="utf-8"))
                self.assertTrue(info["url"].startswith("http://127.0.0.1:"))
                self.assertIn(f"PID {info['pid']}", out)
                with urllib.request.urlopen(info["url"] + "deck.html", timeout=5) as r:
                    self.assertEqual(r.status, 200)
                code, out2, _ = run("preview.py", d, timeout=60)
                self.assertIn("もう表示中", out2)
            finally:
                code, out3, _ = run("preview.py", d, "--stop", timeout=60)
            self.assertEqual(code, 0)
            self.assertIn("止めました", out3)
            self.assertFalse((d / ".shiryo-preview.json").exists())
            time.sleep(0.3)
            with self.assertRaises(OSError):
                urllib.request.urlopen(info["url"], timeout=2)


class Regressions(unittest.TestCase):
    def test_split_css_ignores_style_word_in_comments(self):
        # U3 報告: 追加パーツ集のコメント内の「<style>」を取り違え、:root の変数が消えた
        sys_path_mod = __import__("new_deck")
        html = ("<html><head><!-- 著作権 --><!-- 配色は <style> 冒頭の :root トークン --><style>\n:root{--slide-w:1600px}\n"
                ".slide{zoom:0.8}</style></head><body></body></html>")
        css = sys_path_mod.split_css(html)
        self.assertTrue(css.strip().startswith(":root{--slide-w"), css)

    def test_more_parts_root_tokens_survive(self):
        from _helpers import SCRIPTS
        import new_deck
        css = new_deck.split_css((SCRIPTS.parent / "assets" / "parts" / "freeform_parts_more_16x9.html").read_text(encoding="utf-8"))
        self.assertTrue(css.lstrip().startswith(":root"), css[:80])
        self.assertIn("--slide-w", css)


if __name__ == "__main__":
    unittest.main()
