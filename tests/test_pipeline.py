import json
import os
import shutil
import unittest

import helpers
from PIL import Image

from toonkit import schema
from toonkit.util import norm_text


class SchemaTests(unittest.TestCase):
    def test_norm_text(self):
        self.assertEqual(norm_text("…좋은 질문이네요."), norm_text("... 좋은 질문이네요."))

    def test_storyboard_errors_and_warnings(self):
        sb = {"pages": [{"n": 1, "kind": "bad", "scene": "", "cast": ["zzz"],
                         "lines": [{"id": "a", "kind": "speech", "text": "가" * 41}]}]}
        errs, warns = schema.check_storyboard(sb, {"yunseo"})
        joined = "\n".join(errs)
        self.assertIn("kind", joined)
        self.assertIn("scene", joined)
        self.assertIn("zzz", joined)
        self.assertTrue(any("41자" in w for w in warns))

    def test_example_storyboard_valid(self):
        with open(os.path.join(helpers.EXAMPLE, "episodes/ep01/storyboard.json"), encoding="utf-8") as f:
            sb = json.load(f)
        errs, _ = schema.check_storyboard(sb, {"yunseo"})
        self.assertEqual(errs, [])

    def test_letter_schema(self):
        self.assertTrue(schema.check_letter({"balloons": [{"line": "a", "box": [0.5, 0.5, 0.2, 0.7]}]}))
        self.assertEqual(schema.check_letter({"balloons": [{"line": "a", "box": [0.1, 0.1, 0.3, 0.2]}]}), [])


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.dir, self.root = helpers.temp_series()
        self.png = helpers.make_image(os.path.join(self.dir, "img.png"))
        os.chdir(self.root)

    def tearDown(self):
        os.chdir("/")
        shutil.rmtree(self.dir, ignore_errors=True)

    def t(self, *a):
        return helpers.toon("--root", self.root, *a)

    def ingest_all(self):
        for n in range(1, 9):
            code, o, e = self.t("ingest", "1", str(n), self.png)
            self.assertEqual(code, 0, e)

    def write_letter(self, n, balloons):
        p = os.path.join(self.root, "episodes/ep01/pages/p%02d/letter.json" % n)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"balloons": balloons}, f, ensure_ascii=False)

    def full_letters(self):
        self.write_letter(2, [{"line": "p2a", "box": [0.08, 0.06, 0.5, 0.2], "tail": [0.35, 0.32]}])
        self.write_letter(3, [{"line": "p3a", "box": [0.1, 0.05, 0.9, 0.2], "tail": [0.5, 0.35]},
                              {"line": "p3b", "kind": "sfx", "box": [0.6, 0.5, 0.95, 0.65]}])
        self.write_letter(4, [{"line": "p4a", "box": [0.05, 0.03, 0.4, 0.1]}])
        self.write_letter(5, [{"line": "p5a", "box": [0.1, 0.05, 0.6, 0.2], "tail": [0.4, 0.35]},
                              {"line": "p5b", "box": [0.1, 0.8, 0.9, 0.9]}])
        self.write_letter(6, [{"line": "p6a", "box": [0.1, 0.85, 0.5, 0.93]}])
        self.write_letter(7, [{"line": "p7a", "box": [0.05, 0.03, 0.3, 0.1]}])

    def test_prompt_requires_sheet_then_builds(self):
        code, o, e = self.t("prompt", "1", "--pages", "2")
        self.assertEqual(code, 2)
        self.assertIn("시트", e)
        code, o, e = self.t("prompt", "1", "--pages", "2,6", "--no-sheets")
        self.assertEqual(code, 0, e)
        jobs = json.loads(o)
        self.assertEqual([j["page"] for j in jobs], [2, 6])
        text = open(jobs[1]["prompt_file"], encoding="utf-8").read()
        self.assertTrue(text.startswith("FORMAT:"))
        self.assertTrue(text.rstrip().rsplit("\n\n", 1)[1].startswith("FORMAT:"))
        self.assertIn("NO speech bubbles", text)
        self.assertIn("결제하기", text)
        self.assertIn("see-through bangs", text)
        # 같은 내용으로 다시 만들면 새 버전을 만들지 않는다
        code, o2, e = self.t("prompt", "1", "--pages", "2", "--no-sheets")
        self.assertTrue(json.loads(o2)[0]["prompt_file"].endswith("prompt_v1.txt"))

    def test_cover_prompt_leaves_top_empty(self):
        code, o, e = self.t("prompt", "1", "--pages", "1,8", "--no-sheets")
        jobs = json.loads(o)
        self.assertIn("top 40%", open(jobs[0]["prompt_file"], encoding="utf-8").read())
        self.assertIn("bottom 35%", open(jobs[1]["prompt_file"], encoding="utf-8").read())

    def test_ingest_rejects_landscape(self):
        wide = helpers.make_image(os.path.join(self.dir, "wide.png"), (1400, 1000))
        code, o, e = self.t("ingest", "1", "2", wide)
        self.assertEqual(code, 0)
        self.assertIn("rejected", o)
        pj = json.load(open(os.path.join(self.root, "episodes/ep01/pages/p02/page.json"), encoding="utf-8"))
        self.assertTrue(pj["versions"][0]["rejected"])
        self.assertIsNone(pj["chosen"])
        self.assertTrue(os.path.isfile(os.path.join(self.root, "episodes/ep01/pages/p02/gen_v1.png")))
        code, o, e = self.t("qa", "1")
        self.assertIn("채택할 이미지", o)
        ledger = [json.loads(l) for l in open(os.path.join(self.root, "ledger.jsonl"), encoding="utf-8")]
        self.assertFalse(ledger[-1]["ok"])

    def test_ingest_edit_records_base_and_status(self):
        self.t("ingest", "1", "2", self.png)
        self.t("ingest", "1", "2", self.png, "--edit-of", "1")
        pj = json.load(open(os.path.join(self.root, "episodes/ep01/pages/p02/page.json"), encoding="utf-8"))
        self.assertEqual(pj["versions"][1]["kind"], "edit")
        self.assertEqual(pj["versions"][1]["base"], 1)
        code, o, e = self.t("status", "1")
        self.assertIn("재생성률 50%", o)

    def test_qa_detects_text_mismatch_and_missing(self):
        self.ingest_all()
        self.write_letter(3, [{"line": "p3a", "text": "다른 문장", "box": [0.1, 0.05, 0.9, 0.2]}])
        code, o, e = self.t("qa", "1")
        self.assertEqual(code, 1)
        self.assertIn("문구가 storyboard 와 다릅니다", o)
        self.assertIn("p3b", o)
        self.assertIn("빠졌습니다", o)

    def test_qa_normalizes_ellipsis_and_space(self):
        self.ingest_all()
        self.write_letter(5, [{"line": "p5a", "text": "... 1위는고민할 필요도없지.", "box": [0.1, 0.05, 0.6, 0.2]},
                              {"line": "p5b", "box": [0.1, 0.8, 0.9, 0.9]}])
        self.t("letter", "1", "--pages", "5")
        code, o, e = self.t("qa", "1")
        self.assertNotIn("p5a", o.split("자동 검사")[0].replace("p5a", "", 0) if False else "".join(l for l in o.splitlines() if "문구가" in l))

    def test_qa_overflow_and_out_of_canvas_and_overlap(self):
        self.ingest_all()
        long = "아주 긴 대사 " * 8
        sbp = os.path.join(self.root, "episodes/ep01/storyboard.json")
        sb = json.load(open(sbp, encoding="utf-8"))
        sb["pages"][1]["lines"][0]["text"] = long
        json.dump(sb, open(sbp, "w", encoding="utf-8"), ensure_ascii=False)
        self.write_letter(2, [{"line": "p2a", "box": [0.1, 0.1, 0.25, 0.14], "tail": [0.5, 1.2]}])
        code, o, e = self.t("qa", "1")
        self.assertIn("박스를 넘칩니다", o)
        self.assertIn("캔버스 밖", o)
        self.write_letter(3, [{"line": "p3a", "box": [0.1, 0.1, 0.5, 0.3]}, {"line": "p3b", "kind": "sfx", "box": [0.3, 0.2, 0.7, 0.4]}])
        code, o, e = self.t("qa", "1")
        self.assertIn("겹칩니다", o)

    def test_letter_qa_approve_export(self):
        self.ingest_all()
        self.full_letters()
        code, o, e = self.t("letter", "1")
        self.assertEqual(code, 0, o + e)
        code, o, e = self.t("qa", "1")
        self.assertEqual(code, 0, o)
        self.assertIn("시각 점검", o.replace("직접 보고", "시각 점검") )
        code, o, e = self.t("export", "1")
        self.assertEqual(code, 2)
        self.assertIn("승인", e)
        for n in range(1, 9):
            self.t("approve", "1", str(n))
        code, o, e = self.t("export", "1")
        self.assertEqual(code, 0, e)
        outd = os.path.join(self.root, "episodes/ep01/out")
        for i in range(1, 9):
            with Image.open(os.path.join(outd, "%02d.jpg" % i)) as im:
                self.assertEqual(im.size, (1080, 1350))
        self.assertTrue(os.path.isfile(os.path.join(outd, "preview.jpg")))
        cap = open(os.path.join(outd, "caption.txt"), encoding="utf-8").read()
        self.assertIn("#인스타툰", cap)
        self.assertNotIn("AI 생성", cap)

    def test_off_ratio_rejected_at_ingest_so_export_refuses(self):
        # 0.76 비율은 ingest 에서 rejected 가 되어 내보낼 수 없다
        odd = helpers.make_image(os.path.join(self.dir, "odd.png"), (1064, 1400))
        code, o, e = self.t("ingest", "1", "2", odd)
        self.assertIn("비율", o)
        code, o, e = self.t("export", "1")
        self.assertEqual(code, 2)
        self.assertIn("rejected", e)

    def test_letter_reports_overflow_exit_code(self):
        self.ingest_all()
        sbp = os.path.join(self.root, "episodes/ep01/storyboard.json")
        sb = json.load(open(sbp, encoding="utf-8"))
        sb["pages"][1]["lines"][0]["text"] = "아주 긴 대사 " * 10
        json.dump(sb, open(sbp, "w", encoding="utf-8"), ensure_ascii=False)
        self.write_letter(2, [{"line": "p2a", "box": [0.1, 0.1, 0.25, 0.14]}])
        code, o, e = self.t("letter", "1", "--pages", "2")
        self.assertEqual(code, 1)
        self.assertIn("넘침", o)

    def test_grid(self):
        self.t("ingest", "1", "2", self.png)
        code, o, e = self.t("grid", "1", "2")
        self.assertEqual(code, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.root, "episodes/ep01/pages/p02/grid.png")))

    def test_root_discovery_from_subdir(self):
        os.chdir(os.path.join(self.root, "episodes"))
        code, o, e = helpers.toon("status")
        self.assertEqual(code, 0, e)
        self.assertIn("EP.1", o)

    def test_init_and_character_and_episode(self):
        newdir = os.path.join(self.dir, "fresh")
        code, o, e = helpers.toon("init", newdir, "--title", "테스트툰")
        self.assertEqual(code, 0, e)
        code, o, e = helpers.toon("--root", newdir, "character", "add", "hero", "--name", "히어로", "--role", "support", "--no-style")
        self.assertEqual(code, 0, e)
        sp = open(os.path.join(newdir, "characters/hero/sheet_prompt_v1.txt"), encoding="utf-8").read()
        self.assertIn("3 views", sp.replace("three views", "3 views"))
        code, o, e = helpers.toon("--root", newdir, "character", "ingest", "hero", self.png)
        self.assertEqual(code, 0, e)
        code, o, e = helpers.toon("--root", newdir, "character", "approve", "hero")
        self.assertEqual(code, 0, e)
        code, o, e = helpers.toon("--root", newdir, "episode", "new")
        self.assertEqual(code, 0, e)
        self.assertTrue(os.path.isfile(os.path.join(newdir, "episodes/ep01/storyboard.json")))
        code, o, e = helpers.toon("--root", newdir, "prompt", "1")
        self.assertEqual(code, 2)
        self.assertIn("TODO", e)


if __name__ == "__main__":
    unittest.main()

