import json
import os
import shutil
import time
import unittest

import helpers
from PIL import Image

from toonkit import schema
from toonkit.project import Project
from toonkit.util import RATIO_MAX, RATIO_MIN, ToonError, crop_box, parse_color


class Base(unittest.TestCase):
    def setUp(self):
        self.dir, self.root = helpers.temp_series()
        self.png = helpers.make_image(os.path.join(self.dir, "img.png"))
        os.chdir(self.root)

    def tearDown(self):
        os.chdir("/")
        shutil.rmtree(self.dir, ignore_errors=True)

    def t(self, *a):
        return helpers.toon("--root", self.root, *a)

    def pp(self, n, name):
        return os.path.join(self.root, "episodes/ep01/pages/p%02d" % n, name)

    def page_json(self, n):
        with open(self.pp(n, "page.json"), encoding="utf-8") as f:
            return json.load(f)

    def save_page_json(self, n, pj):
        with open(self.pp(n, "page.json"), "w", encoding="utf-8") as f:
            json.dump(pj, f)

    def ingest_all(self):
        for n in range(1, 9):
            code, o, e = self.t("ingest", "1", str(n), self.png)
            self.assertEqual(code, 0, e)

    def write_letter(self, n, balloons):
        p = self.pp(n, "letter.json")
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

    def ready(self):
        """8장 모두 등록, 식자, qa 통과."""
        self.ingest_all()
        self.full_letters()
        self.assertEqual(self.t("letter", "1")[0], 0)
        self.assertEqual(self.t("qa", "1")[0], 0)

    def approve_all(self):
        for n in range(1, 9):
            self.assertEqual(self.t("approve", "1", str(n))[0], 0)


class FreshnessTests(Base):  # 높음 1
    def test_approve_rejects_after_new_version(self):
        self.ready()
        self.t("ingest", "1", "2", self.png)  # v2 채택, 식자는 v1 기준
        code, o, e = self.t("approve", "1", "2")
        self.assertEqual(code, 2)
        self.assertIn("toon letter 를 다시 실행하세요", e)

    def test_approve_rejects_when_letter_json_newer(self):
        self.ready()
        future = time.time() + 100
        os.utime(self.pp(2, "letter.json"), (future, future))
        code, o, e = self.t("approve", "1", "2")
        self.assertEqual(code, 2)
        self.assertIn("toon letter 를 다시 실행하세요", e)

    def test_approve_version_does_not_persist_on_failure(self):
        self.ready()
        self.t("ingest", "1", "2", self.png)
        self.t("approve", "1", "2", "--version", "1")  # lettered 는 v1 기준이라 통과
        self.assertEqual(self.page_json(2)["chosen"], 1)
        self.assertTrue(self.page_json(2)["approved"])

    def test_export_rejects_stale(self):
        self.ready()
        self.approve_all()
        self.t("ingest", "1", "3", self.png)
        code, o, e = self.t("export", "1")
        self.assertEqual(code, 2)
        self.assertIn("3장", e)
        self.assertIn("toon letter 를 다시 실행하세요", e)
        code, o, e = self.t("export", "1", "--force")
        self.assertEqual(code, 2)

    def test_relettering_unapproves(self):
        self.ready()
        self.t("approve", "1", "2")
        self.assertTrue(self.page_json(2)["approved"])
        code, o, e = self.t("letter", "1", "--pages", "2")
        self.assertEqual(code, 0)
        self.assertIn("승인을 해제", o)
        self.assertFalse(self.page_json(2)["approved"])

    def test_ingest_new_version_unapproves(self):
        self.ready()
        self.t("approve", "1", "2")
        self.t("ingest", "1", "2", self.png)
        self.assertFalse(self.page_json(2)["approved"])


class RejectedTests(Base):  # 높음 2
    def wide(self):
        return helpers.make_image(os.path.join(self.dir, "wide.png"), (1400, 1000))

    def test_fallback_excludes_rejected(self):
        self.t("ingest", "1", "2", self.png)
        self.t("ingest", "1", "2", self.wide())
        pj = self.page_json(2)
        pj["chosen"] = None
        self.save_page_json(2, pj)
        v, src = Project.open(self.root).chosen_file(1, 2)
        self.assertEqual(v, 1)

    def test_all_rejected_gives_none_with_hint(self):
        self.t("ingest", "1", "2", self.wide())
        proj = Project.open(self.root)
        self.assertEqual(proj.chosen_file(1, 2), (None, None))
        self.assertIn("rejected", proj.no_image_hint(1, 2))
        code, o, e = self.t("letter", "1", "--pages", "2")
        self.assertIn("rejected", o)

    def test_approve_refuses_rejected_chosen(self):
        self.ready()
        pj = self.page_json(2)
        pj["versions"][0]["rejected"] = True
        self.save_page_json(2, pj)
        code, o, e = self.t("approve", "1", "2")
        self.assertEqual(code, 2)
        self.assertIn("rejected", e)

    def test_grid_and_letter_refuse_rejected_chosen(self):
        self.t("ingest", "1", "2", self.png)
        pj = self.page_json(2)
        pj["versions"][0]["rejected"] = True
        self.save_page_json(2, pj)
        for cmd in (("grid", "1", "2"), ("letter", "1", "--pages", "2")):
            code, o, e = self.t(*cmd)
            self.assertEqual(code, 2, cmd)
            self.assertIn("rejected", e)


class ExportTests(Base):  # 중간 3
    def test_foreign_files_kept_and_stale_pages_removed(self):
        self.ready()
        self.approve_all()
        out = os.path.join(self.root, "episodes/ep01/out")
        os.makedirs(out)
        for name in ("notes.txt", "09.jpg"):
            open(os.path.join(out, name), "w").write("x")
        open(os.path.join(out, "99.png"), "w").write("mine")
        self.assertEqual(self.t("export", "1")[0], 0)
        self.assertTrue(os.path.isfile(os.path.join(out, "notes.txt")))
        self.assertTrue(os.path.isfile(os.path.join(out, "99.png")))
        self.assertFalse(os.path.exists(os.path.join(out, "09.jpg")))
        self.assertTrue(os.path.isfile(os.path.join(out, "08.jpg")))
        self.assertFalse(os.path.exists(out + ".tmp"))

    def test_failure_leaves_previous_out_untouched(self):
        self.ready()
        self.approve_all()
        self.assertEqual(self.t("export", "1")[0], 0)
        out = os.path.join(self.root, "episodes/ep01/out")
        before = open(os.path.join(out, "01.jpg"), "rb").read()
        self.t("letter", "1", "--pages", "4")  # 4장 승인 해제
        code, o, e = self.t("export", "1")
        self.assertEqual(code, 2)
        self.assertEqual(open(os.path.join(out, "01.jpg"), "rb").read(), before)
        self.assertFalse(os.path.exists(out + ".tmp"))

    def test_export_ratio_defense_on_lettered(self):
        self.ready()
        self.approve_all()
        Image.new("RGB", (1064, 1400), (255, 255, 255)).save(self.pp(4, "lettered.png"))
        code, o, e = self.t("export", "1")
        self.assertEqual(code, 2)
        self.assertIn("비율", e)


class RatioTests(Base):  # 중간 4
    def test_shared_constants_and_ingest_boundaries(self):
        self.assertEqual((RATIO_MIN, RATIO_MAX), (0.78, 0.82))
        bad = helpers.make_image(os.path.join(self.dir, "bad.png"), (1064, 1400))  # 0.76
        code, o, e = self.t("ingest", "1", "2", bad)
        self.assertIn("rejected", o)
        ok = helpers.make_image(os.path.join(self.dir, "ok.png"), (1106, 1400))  # 0.79
        code, o, e = self.t("ingest", "1", "3", ok)
        self.assertNotIn("rejected", o)

    def test_qa_flags_balloon_outside_export_crop(self):
        wide = helpers.make_image(os.path.join(self.dir, "w.png"), (1148, 1400))  # 0.82 → 좌우 14px 잘림
        self.assertEqual(crop_box(1148, 1400, 1080, 1350), (14, 0, 1134, 1400))
        self.t("ingest", "1", "4", wide)
        self.write_letter(4, [{"line": "p4a", "box": [0.01, 0.03, 0.4, 0.1]}])
        self.t("letter", "1", "--pages", "4")
        code, o, e = self.t("qa", "1")
        self.assertIn("크롭 영역 밖", o)


class WrapperTests(unittest.TestCase):  # 중간 5, 6
    def test_script_text(self):
        with open(os.path.join(helpers.SKILL, "scripts", "toon"), encoding="utf-8") as f:
            s = f.read()
        self.assertIn("uv run --no-project --quiet --with pillow", s)
        self.assertIn('${XDG_CACHE_HOME:-$HOME/.cache}/instatoon/venv', s)
        self.assertIn('import PIL', s)
        self.assertIn("3, 9", s)
        self.assertNotIn("$SKILL/.venv", s)


class RootAndIdTests(Base):  # 중간 7, 8
    def test_explicit_root_does_not_search_upward(self):
        sub = os.path.join(self.root, "episodes")
        code, o, e = helpers.toon("--root", sub, "status")
        self.assertEqual(code, 2)
        self.assertIn("series.json", e)

    def test_character_id_validated(self):
        for bad in ("../evil", "a/b", "한글", ""):
            code, o, e = self.t("character", "add", bad)
            self.assertEqual(code, 2, bad)
            self.assertIn("영문", e)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "evil")))

    def test_cast_id_validated(self):
        errs, _ = schema.check_storyboard({"pages": [{"n": 1, "kind": "body", "scene": "x", "cast": ["../a"]}]}, {"yunseo"})
        self.assertTrue(any("영문" in x for x in errs))


class LowTests(Base):
    def test_corrupt_image_leaves_no_orphans(self):
        bad = os.path.join(self.dir, "bad.png")
        open(bad, "wb").write(b"not an image")
        code, o, e = self.t("ingest", "1", "2", bad)
        self.assertEqual(code, 2)
        self.assertIn("손상", e)
        self.assertFalse(os.path.exists(self.pp(2, "gen_v1.png")))
        self.assertFalse(os.path.exists(self.pp(2, "page.json")))
        code, o, e = self.t("character", "ingest", "yunseo", bad)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(os.path.join(self.root, "characters/yunseo/sheet_v1.png")))

    def test_parse_color(self):
        self.assertEqual(parse_color("#f00", "#000000"), (255, 0, 0))
        self.assertEqual(parse_color("#E02020", "#000000"), (224, 32, 32))
        self.assertEqual(parse_color(None, "#111"), (17, 17, 17))
        for bad in ("red", "#12345", "#GGGGGG", "E02020"):
            with self.assertRaises(ToonError):
                parse_color(bad, "#000")
        s = {"title": "t", "cover": {"accent_color": "red"}}
        self.assertTrue(any("accent_color" in x for x in schema.check_series(s)))

    def test_prompt_merges_jobs_and_stores_relative_paths(self):
        self.t("prompt", "1", "--pages", "2", "--no-sheets")
        code, o, e = self.t("prompt", "1", "--pages", "6", "--no-sheets")
        jobs = json.loads(o)
        self.assertEqual([j["page"] for j in jobs], [6])
        self.assertTrue(os.path.isabs(jobs[0]["prompt_file"]))
        jp = os.path.join(self.root, "episodes/ep01/jobs.json")
        stored = json.load(open(jp, encoding="utf-8"))
        self.assertEqual([j["page"] for j in stored], [2, 6])
        for j in stored:
            self.assertFalse(os.path.isabs(j["prompt_file"]), j)
        self.t("ingest", "1", "2", self.png)
        ent = self.page_json(2)["versions"][0]
        self.assertFalse(os.path.isabs(ent["prompt_file"]))
        self.assertTrue(os.path.isfile(os.path.join(self.root, ent["prompt_file"])))

    def test_old_absolute_jobs_readable(self):
        self.t("prompt", "1", "--pages", "2", "--no-sheets")
        jp = os.path.join(self.root, "episodes/ep01/jobs.json")
        stored = json.load(open(jp, encoding="utf-8"))
        stored[0]["prompt_file"] = os.path.join(self.root, stored[0]["prompt_file"])
        json.dump(stored, open(jp, "w", encoding="utf-8"))
        code, o, e = self.t("ingest", "1", "2", self.png)
        self.assertEqual(code, 0, e)
        self.assertFalse(os.path.isabs(self.page_json(2)["versions"][0]["prompt_file"]))
        code, o, e = self.t("prompt", "1", "--pages", "3", "--no-sheets")
        self.assertEqual(code, 0, e)
        self.assertEqual([j["page"] for j in json.load(open(jp, encoding="utf-8"))], [2, 3])

    def test_bad_shapes_give_friendly_errors(self):
        self.ingest_all()
        sbp = os.path.join(self.root, "episodes/ep01/storyboard.json")
        sb = json.load(open(sbp, encoding="utf-8"))
        sb["pages"][1]["lines"] = ["문자열"]
        json.dump(sb, open(sbp, "w", encoding="utf-8"), ensure_ascii=False)
        for cmd in (("letter", "1"), ("qa", "1")):
            code, o, e = self.t(*cmd)
            self.assertEqual(code, 2, cmd)
            self.assertIn("콘티 검증 실패", e)
        shutil.copyfile(os.path.join(helpers.EXAMPLE, "episodes/ep01/storyboard.json"), sbp)
        with open(self.pp(2, "letter.json"), "w", encoding="utf-8") as f:
            json.dump([1, 2], f)
        code, o, e = self.t("letter", "1", "--pages", "2")
        self.assertEqual(code, 2)
        self.assertIn("letter.json", e)
        code, o, e = self.t("qa", "1")
        self.assertIn("letter.json", o)
        self.assertNotIn("Traceback", e)

    def test_canvas_must_be_4_5(self):
        self.assertTrue(schema.check_series({"title": "t", "canvas": [1080, 1080]}))
        self.assertTrue(schema.check_series({"title": "t", "canvas": [1080, 1920]}))
        self.assertEqual(schema.check_series({"title": "t", "canvas": [1080, 1350]}), [])
        sp = os.path.join(self.root, "series.json")
        s = json.load(open(sp, encoding="utf-8"))
        s["canvas"] = [1000, 1000]
        json.dump(s, open(sp, "w", encoding="utf-8"), ensure_ascii=False)
        code, o, e = self.t("prompt", "1", "--pages", "2", "--no-sheets")
        self.assertEqual(code, 2)
        self.assertIn("4:5", e)

    def test_approve_blocked_by_qa_errors_unless_force(self):
        self.ready()
        self.write_letter(3, [{"line": "p3a", "text": "다른 문장", "box": [0.1, 0.05, 0.9, 0.2]}])
        self.t("letter", "1", "--pages", "3")
        self.assertEqual(self.t("qa", "1")[0], 1)
        code, o, e = self.t("approve", "1", "3")
        self.assertEqual(code, 2)
        self.assertIn("qa", e)
        self.assertFalse(self.page_json(3).get("approved"))
        code, o, e = self.t("approve", "1", "3", "--force")
        self.assertEqual(code, 0, e)
        self.assertTrue(self.page_json(3)["approved"])


if __name__ == "__main__":
    unittest.main()
