import json
import os
import unittest

import helpers
from PIL import Image

from toonkit import prompts, styles
from toonkit.project import Project


def rj(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class StyleBase(unittest.TestCase):
    def setUp(self):
        self.dir = __import__("tempfile").mkdtemp(prefix="toonstyle_")
        self.root = os.path.join(self.dir, "s")
        code, o, e = helpers.toon("init", self.root, "--title", "테스트툰")
        assert code == 0, e
        helpers.approve_plan(self.root)
        self.good = helpers.make_image(os.path.join(self.dir, "good.png"))
        self.wide = helpers.make_image(os.path.join(self.dir, "wide.png"), size=(1400, 1000))

    def t(self, *a):
        return helpers.toon("--root", self.root, *a)

    def series(self):
        return rj(os.path.join(self.root, "series.json"))

    def approved_style(self, preset="bw_manga"):
        self.assertEqual(self.t("style", "set", "--preset", preset)[0], 0)
        self.assertEqual(self.t("style", "ingest", self.good, "--preset", preset)[0], 0)
        code, o, e = self.t("style", "approve")
        self.assertEqual(code, 0, e)


class PresetTests(StyleBase):
    def test_preset_data(self):
        self.assertGreaterEqual(len(styles.PRESETS), 7)
        for p in styles.PRESETS:
            for k in ("id", "name", "summary", "audience", "bible", "palette", "accent", "font"):
                self.assertTrue(p.get(k), (p["id"], k))
            self.assertIn(p["palette"], styles.PALETTES)

    def test_presets_listing(self):
        code, o, e = self.t("style", "presets")
        self.assertEqual(code, 0, e)
        for p in styles.PRESETS:
            self.assertIn(p["id"], o)

    def test_init_has_empty_style(self):
        st = self.series()["style"]
        self.assertIsNone(st["preset"])
        self.assertEqual(st["samples"], [])
        self.assertTrue(os.path.isdir(os.path.join(self.root, "style")))

    def test_set_preset_fills_and_accent(self):
        code, o, e = self.t("style", "set", "--preset", "doodle")
        self.assertEqual(code, 0, e)
        s = self.series()
        self.assertEqual(s["style"]["preset"], "doodle")
        self.assertEqual(s["style"]["palette"], "mono_accent")
        self.assertEqual(s["style"]["bible"], styles.get_preset("doodle")["bible"])
        self.assertEqual(s["cover"]["accent_color"], styles.get_preset("doodle")["accent"])

    def test_set_preset_keeps_custom_accent(self):
        p = os.path.join(self.root, "series.json")
        s = rj(p)
        s["cover"]["accent_color"] = "#112233"
        json.dump(s, open(p, "w"))
        self.t("style", "set", "--preset", "doodle")
        self.assertEqual(self.series()["cover"]["accent_color"], "#112233")

    def test_set_bible_and_palette(self):
        code, o, e = self.t("style", "set", "--bible", "thick brush lines", "--palette", "color")
        self.assertEqual(code, 0, e)
        st = self.series()["style"]
        self.assertEqual((st["preset"], st["bible"], st["palette"]), (None, "thick brush lines", "color"))

    def test_set_errors(self):
        self.assertEqual(self.t("style", "set")[0], 2)
        self.assertEqual(self.t("style", "set", "--preset", "nope")[0], 2)
        self.assertEqual(self.t("style", "set", "--preset", "doodle", "--bible", "x")[0], 2)

    def test_presets_have_no_artist_names(self):
        blob = " ".join(p["bible"] + p["summary"] for p in styles.PRESETS).lower()
        for bad in ("ghibli", "miyazaki", "disney", "pixar", "naver", "kakao"):
            self.assertNotIn(bad, blob)


class RefTests(StyleBase):
    def test_ref_add_and_list(self):
        code, o, e = self.t("style", "ref", "add", self.good, self.wide)
        self.assertEqual(code, 0, e)
        refs = self.series()["style"]["references"]
        self.assertEqual(refs, ["style/refs/ref_01.png", "style/refs/ref_02.png"])
        self.assertTrue(os.path.isfile(os.path.join(self.root, refs[1])))
        code, o, e = self.t("style", "ref", "add", self.good)
        self.assertEqual(self.series()["style"]["references"][-1], "style/refs/ref_03.png")
        code, o, e = self.t("style", "ref", "list")
        self.assertIn("ref_01.png", o)

    def test_ref_add_rejects_bad_image(self):
        bad = os.path.join(self.dir, "bad.png")
        open(bad, "w").write("not an image")
        code, o, e = self.t("style", "ref", "add", bad)
        self.assertEqual(code, 2)
        self.assertEqual(self.series()["style"]["references"], [])


class PromptTests(StyleBase):
    def jobs(self, *extra):
        code, o, e = self.t("style", "prompt", *extra)
        self.assertEqual(code, 0, e)
        return json.loads(o)

    def test_three_presets_same_scene(self):
        jobs = self.jobs("--presets", "bw_manga,doodle,chibi")
        self.assertEqual([j["preset"] for j in jobs], ["bw_manga", "doodle", "chibi"])
        texts = [open(j["prompt_file"], encoding="utf-8").read() for j in jobs]
        self.assertEqual(len(set(j["prompt_file"] for j in jobs)), 3)
        for t, pid in zip(texts, ("bw_manga", "doodle", "chibi")):
            self.assertIn(styles.get_preset(pid)["bible"], t)
            self.assertIn("generic young office worker", t)
            self.assertIn("NO text", t)
            self.assertTrue(t.startswith("FORMAT:") and t.rstrip().endswith("Never landscape, never square."))
            self.assertNotIn("Match the drawing style", t)
        self.assertEqual(jobs[0]["referenced_image_paths"], [])
        self.assertIn("sample_prompt_v1_doodle.txt", jobs[1]["prompt_file"])

    def test_custom_scene(self):
        jobs = self.jobs("--presets", "doodle", "--scene", "a cat on a sofa")
        self.assertIn("SCENE: a cat on a sofa", open(jobs[0]["prompt_file"], encoding="utf-8").read())

    def test_refs_included(self):
        self.t("style", "ref", "add", self.good)
        jobs = self.jobs("--presets", "bw_manga,doodle")
        for j in jobs:
            self.assertEqual(j["referenced_image_paths"], [os.path.join(self.root, "style/refs/ref_01.png")])
            self.assertIn("Match the drawing style of the attached reference image(s)", open(j["prompt_file"], encoding="utf-8").read())

    def test_current_style_single(self):
        self.t("style", "set", "--preset", "flat_color")
        jobs = self.jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["preset"], "flat_color")
        jobs2 = self.jobs()
        self.assertIn("sample_prompt_v2_flat_color.txt", jobs2[0]["prompt_file"])

    def test_prompt_errors(self):
        self.assertEqual(self.t("style", "prompt", "--presets", "nope")[0], 2)


class IngestApproveTests(StyleBase):
    def test_ingest_rejects_ratio(self):
        code, o, e = self.t("style", "ingest", self.wide)
        self.assertEqual(code, 0)
        self.assertIn("rejected", o)
        s = self.series()["style"]["samples"][0]
        self.assertTrue(s["rejected"])
        self.assertTrue(os.path.isfile(os.path.join(self.root, s["file"])))
        code, o, e = self.t("style", "approve")
        self.assertEqual(code, 2)
        code, o, e = self.t("style", "approve", "--version", "1")
        self.assertEqual(code, 2)
        self.assertIn("rejected", e)

    def test_ingest_ok_and_default_approve_skips_rejected(self):
        self.t("style", "ingest", self.good)
        self.t("style", "ingest", self.wide)
        self.assertEqual(self.t("style", "approve")[0], 0)
        st = self.series()["style"]
        self.assertEqual(st["approved_sample"], "style/sample_v1.png")
        self.assertEqual([s["version"] for s in st["samples"]], [1, 2])

    def test_ingest_invalid(self):
        self.assertEqual(self.t("style", "ingest", os.path.join(self.dir, "none.png"))[0], 2)
        self.assertEqual(self.t("style", "ingest", self.good, "--preset", "nope")[0], 2)

    def test_approve_syncs_preset_bible(self):
        self.t("style", "set", "--preset", "bw_manga")
        self.t("style", "ingest", self.good, "--preset", "chibi")
        code, o, e = self.t("style", "approve")
        self.assertEqual(code, 0, e)
        st = self.series()["style"]
        self.assertEqual(st["preset"], "chibi")
        self.assertEqual(st["bible"], styles.get_preset("chibi")["bible"])
        self.assertEqual(st["palette"], "color")
        self.assertEqual(st["approved_sample"], "style/sample_v1.png")

    def test_set_change_releases_approval(self):
        self.approved_style("bw_manga")
        code, o, e = self.t("style", "set", "--preset", "doodle")
        self.assertEqual(code, 0)
        self.assertIn("승인을 해제", o)
        self.assertIsNone(self.series()["style"]["approved_sample"])

    def test_set_same_value_keeps_approval(self):
        self.approved_style("bw_manga")
        self.t("style", "set", "--preset", "bw_manga")
        self.assertEqual(self.series()["style"]["approved_sample"], "style/sample_v1.png")

    def test_status_line(self):
        code, o, e = self.t("status")
        self.assertIn("그림체: 미설정", o)
        self.approved_style("doodle")
        self.t("style", "ref", "add", self.good)
        code, o, e = self.t("status")
        self.assertIn("프리셋 doodle", o)
        self.assertIn("레퍼런스 1장", o)
        self.assertIn("샘플 1장", o)
        self.assertIn("style/sample_v1.png", o)


class CharacterGateTests(StyleBase):
    def test_character_add_blocked_before_approval(self):
        code, o, e = self.t("character", "add", "hero", "--name", "히어로")
        self.assertEqual(code, 2)
        self.assertIn("toon style", e)
        self.assertFalse(os.path.exists(os.path.join(self.root, "characters/hero")))

    def test_no_style_bypass(self):
        code, o, e = self.t("character", "add", "hero", "--name", "히어로", "--no-style")
        self.assertEqual(code, 0, e)
        code, o, e = self.t("character", "prompt", "hero")
        self.assertEqual(code, 2)
        code, o, e = self.t("character", "prompt", "hero", "--no-style")
        self.assertEqual(code, 0, e)
        self.assertIn("[]", o)

    def test_legacy_series_warns_only(self):
        p = os.path.join(self.root, "series.json")
        s = rj(p)
        del s["style"]
        s["style_bible"] = "Watercolor style, soft."
        json.dump(s, open(p, "w"))
        self.assertEqual(self.t("character", "add", "hero", "--no-style")[0], 0)
        self.assertEqual(self.t("character", "ingest", "hero", self.good)[0], 0)
        self.assertEqual(self.t("character", "approve", "hero")[0], 0)
        code, o, e = self.t("character", "prompt", "hero")
        self.assertEqual(code, 0, e)
        self.assertIn("경고", o)

    def test_template_default_series_not_legacy(self):
        self.assertEqual(self.t("character", "add", "hero", "--no-style")[0], 0)
        self.t("character", "ingest", "hero", self.good)
        self.t("character", "approve", "hero")
        self.assertEqual(self.t("character", "prompt", "hero")[0], 2)

    def test_sheet_prompt_refs_start_with_sample(self):
        self.approved_style("pastel_watercolor")
        code, o, e = self.t("character", "add", "hero", "--name", "히어로")
        self.assertEqual(code, 0, e)
        sample = os.path.join(self.root, "style/sample_v1.png")
        self.assertIn(json.dumps([sample]), o)
        sp = open(os.path.join(self.root, "characters/hero/sheet_prompt_v1.txt"), encoding="utf-8").read()
        self.assertIn("Match the drawing style of the first attached image (style sample)", sp)
        self.assertIn(styles.get_preset("pastel_watercolor")["bible"], sp)
        proj = Project.open(self.root)
        self.assertEqual(prompts.sheet_refs(proj), [sample])
        code, o, e = self.t("character", "prompt", "hero")
        self.assertEqual(code, 0, e)
        self.assertIn(json.dumps([sample]), o)

    def test_page_prompt_has_no_sample_in_refs(self):
        self.approved_style("bw_manga")
        self.t("character", "add", "hero", "--name", "히어로")
        self.t("character", "ingest", "hero", self.good)
        self.t("character", "approve", "hero")
        self.assertEqual(self.t("episode", "new")[0], 0)
        sbp = os.path.join(self.root, "episodes/ep01/storyboard.json")
        sb = rj(sbp)
        for p in sb["pages"]:
            p["scene"] = "a quiet room"
            p["cast"] = ["hero"]
        json.dump(sb, open(sbp, "w"))
        code, o, e = self.t("prompt", "1", "--pages", "2")
        self.assertEqual(code, 0, e)
        job = json.loads(o[o.index("["):])[0]
        self.assertEqual(job["referenced_image_paths"], [os.path.join(self.root, "characters/hero/sheet_v1.png")])
        self.assertNotIn("sample_v1", json.dumps(job))
        text = open(job["prompt_file"], encoding="utf-8").read()
        self.assertIn("STYLE: " + styles.get_preset("bw_manga")["bible"], text)

    def test_style_bible_fallback_when_style_empty(self):
        proj = Project.open(self.root)
        p = os.path.join(self.root, "series.json")
        s = rj(p)
        s["style_bible"] = "legacy paragraph"
        json.dump(s, open(p, "w"))
        self.assertEqual(Project.open(self.root).style_bible(), "legacy paragraph")
        self.t("style", "set", "--bible", "new paragraph")
        self.assertEqual(Project.open(self.root).style_bible(), "new paragraph")


if __name__ == "__main__":
    unittest.main()

