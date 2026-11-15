import json
import os
import re
import unittest

import helpers
from PIL import Image

from test_review import Base
from toonkit import formats, lettering, schema, sponsor
from toonkit.project import Project

MD = os.path.join(helpers.SKILL, "references", "formats.md")


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jsave(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


class RegistryTests(unittest.TestCase):
    def test_ids_match_formats_md(self):
        with open(MD, encoding="utf-8") as f:
            ids = re.findall(r"^## \d+\. (\w+) —", f.read(), re.M)
        self.assertEqual(ids, formats.ORDER)
        self.assertEqual(len(ids), 16)

    def test_registry_shape(self):
        for fid, f in formats.FORMATS.items():
            lo, hi = f["pages"]
            self.assertLessEqual(lo, hi)
            self.assertLessEqual(hi, 20)
            self.assertIn(f["ending_type"], ("series", "continue", "cta"))
            self.assertEqual(f["sponsored"], fid in ("sponsored", "groupbuy"))
            n = len(formats.expand_roles(f))
            self.assertTrue(lo <= n <= hi, fid)
        self.assertEqual(formats.get("serial")["pages"], (8, 20))
        self.assertEqual(formats.get("reader")["pages"], (5, 7))
        self.assertEqual(formats.get("groupbuy")["pages"], (8, 10))


class FormatCmdTests(Base):
    def test_list_and_detail(self):
        code, o, e = self.t("formats")
        self.assertEqual(code, 0)
        for fid in formats.ORDER:
            self.assertIn(fid, o)
        code, o, e = self.t("formats", "serial")
        self.assertEqual(code, 0)
        self.assertIn("갈등 확대", o)
        self.assertEqual(self.t("formats", "nope")[0], 2)

    def test_episode_new_template(self):
        code, o, e = self.t("episode", "new", "--format", "quiz")
        self.assertEqual(code, 0, e)
        d = os.path.join(self.root, "episodes", "ep02")
        sb = jload(os.path.join(d, "storyboard.json"))
        pages = sb["pages"]
        self.assertEqual(len(pages), 7)
        self.assertEqual([p["kind"] for p in pages], ["cover"] + ["body"] * 5 + ["ending"])
        self.assertIn("표지: 문제", pages[0]["scene"])
        self.assertEqual(jload(os.path.join(d, "episode.json"))["format"], "quiz")
        errs, warns = schema.check_storyboard(sb, set(), formats.get("quiz"))
        self.assertEqual(errs, [])

    def test_episode_new_default_ranking_and_sponsored(self):
        self.assertEqual(self.t("episode", "new")[0], 0)
        self.assertEqual(jload(os.path.join(self.root, "episodes/ep02/episode.json"))["format"], "ranking")
        self.assertEqual(self.t("episode", "new", "--format", "groupbuy")[0], 0)
        epj = jload(os.path.join(self.root, "episodes/ep03/episode.json"))
        self.assertEqual(epj["sponsored"]["label"], "광고")

    def test_unknown_format_rejected(self):
        code, o, e = self.t("episode", "new", "--format", "bogus")
        self.assertEqual(code, 2)
        self.assertIn("ranking", e)
        self.assertFalse(os.path.exists(os.path.join(self.root, "episodes/ep02")))


class PageCountTests(unittest.TestCase):
    def pages(self, n):
        return {"pages": [{"n": i, "kind": "body", "scene": "x", "cast": ["a"]} for i in range(1, n + 1)]}

    def test_range_warning_by_format(self):
        _, w = schema.check_storyboard(self.pages(8), {"a"}, formats.get("reader"))
        self.assertTrue(any("5~7" in x for x in w))
        _, w = schema.check_storyboard(self.pages(7), {"a"}, formats.get("quiz"))
        self.assertFalse(any("장 수" in x for x in w))
        _, w = schema.check_storyboard(self.pages(14), {"a"}, formats.get("serial"))
        self.assertFalse(any("장 수" in x for x in w))
        _, w = schema.check_storyboard(self.pages(14), {"a"}, None)
        self.assertTrue(any("권장 6~10" in x for x in w))

    def test_hard_max_20(self):
        e, _ = schema.check_storyboard(self.pages(20), {"a"}, formats.get("serial"))
        self.assertEqual(e, [])
        e, _ = schema.check_storyboard(self.pages(21), {"a"}, formats.get("serial"))
        self.assertTrue(any("20장" in x for x in e))
        e, _ = schema.check_storyboard(self.pages(21), {"a"}, None)
        self.assertTrue(any("20장" in x for x in e))


class CoverChipTests(Base):
    def cover_pixels(self, **page_extra):
        sbp = os.path.join(self.root, "episodes/ep01/storyboard.json")
        sb = jload(sbp)
        sb["pages"][0].update(page_extra)
        jsave(sbp, sb)
        self.assertEqual(self.t("ingest", "1", "1", self.png)[0], 0)
        self.assertEqual(self.t("letter", "1", "--pages", "1")[0], 0)
        return Image.open(self.pp(1, "lettered.png")).convert("RGB")

    def test_subtitle_and_note_render(self):
        im = self.cover_pixels(cover_subtitle="(1) 절친과 남편의 첫상담", cover_note="실제 사연을 각색했습니다")
        W, H = im.size
        proj = Project.open(self.root)
        text = "(1) 절친과 남편의 첫상담"
        probe = lettering.subtitle_chip_box(proj, W, H, text, 0)
        area_bottom = proj.series["cover"]["title_area"][3] * H
        top = area_bottom - (probe[3] - probe[1]) - 14 * W / 1080.0
        x0, y0, x1, y1, _ = lettering.subtitle_chip_box(proj, W, H, text, top)
        self.assertTrue(0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H)
        self.assertLessEqual(y1, area_bottom + 1)  # 부제 칩은 제목 영역 안(캐릭터 영역 침범 금지)
        a = proj.series["cover"]["accent_color"].lstrip("#")
        accent = tuple(int(a[i:i + 2], 16) for i in (0, 2, 4))
        self.assertEqual(im.getpixel((int(x0) + 6, int((y0 + y1) / 2))), accent)
        gray = [im.getpixel((x, y)) for x in range(20, int(W * 0.5)) for y in range(H - 50, H - 10)]
        self.assertTrue(any(abs(c[0] - 120) < 8 and abs(c[1] - 120) < 8 for c in gray))

    def test_long_subtitle_stays_inside(self):
        proj = Project.open(self.root)
        x0, y0, x1, y1, _ = lettering.subtitle_chip_box(proj, 1080, 1350, "아주 긴 부제 " * 12, 513)
        self.assertTrue(x0 >= 0 and x1 <= 1080 and y1 <= 1350)

    def test_bad_subtitle_type_is_error(self):
        e, _ = schema.check_storyboard({"pages": [{"n": 1, "kind": "cover", "scene": "x", "cast": [], "cover_title": ["a", "b", "c"],
                                                   "cover_subtitle": 3}]}, set())
        self.assertTrue(any("cover_subtitle" in x for x in e))


class EndingTests(Base):
    def last(self, **epj_extra):
        epp = os.path.join(self.root, "episodes/ep01/episode.json")
        ej = jload(epp)
        ej.update(epj_extra)
        jsave(epp, ej)
        self.assertEqual(self.t("ingest", "1", "8", self.png)[0], 0)
        self.assertEqual(self.t("letter", "1", "--pages", "8")[0], 0)
        return Image.open(self.pp(8, "lettered.png")).convert("RGB")

    def dark_bottom_center(self, im):
        W, H = im.size
        return sum(1 for x in range(int(W * 0.3), int(W * 0.7)) for y in range(H - 110, H - 30) if sum(im.getpixel((x, y))) < 150)

    def test_continue_renders(self):
        base = self.last()
        cont = self.last(ending="continue")
        self.assertGreater(self.dark_bottom_center(cont), 500)  # "- 계속 -" 글자
        W, H = base.size
        band = lambda im: sum(1 for x in range(0, W, 3) for y in range(int(H * 0.68), int(H * 0.9), 3) if sum(im.getpixel((x, y))) < 150)
        self.assertLess(band(cont), band(base))  # 시리즈 엔딩의 팔로우 칩이 없다
        self.assertNotEqual(base.tobytes(), cont.tobytes())

    def test_final_forces_series_ending(self):
        base = self.last()
        fin = self.last(ending="continue", final=True)
        self.assertEqual(base.tobytes(), fin.tobytes())

    def test_format_continue_and_custom_text(self):
        self.assertEqual(lettering.ending_mode({"format": "serial"}), "continue")
        self.assertEqual(lettering.ending_mode({"format": "serial", "final": True}), "series")
        self.assertEqual(lettering.ending_mode({"format": "ranking"}), "series")
        a = self.last(ending="continue")
        b = self.last(ending="continue", continue_text="- 다음 화에 계속 -")
        self.assertNotEqual(a.tobytes(), b.tobytes())


class SponsoredTests(Base):
    def set_ep(self, **kw):
        epp = os.path.join(self.root, "episodes/ep01/episode.json")
        ej = jload(epp)
        ej.update(kw)
        jsave(epp, ej)

    def test_caption_first_line(self):
        ej = {"caption": "오늘의 이야기", "sponsored": {"label": "유료 광고"}}
        self.assertEqual(sponsor.caption_text(ej).split("\n")[0], "#유료광고")
        ej["caption"] = "#유료광고 오늘의 이야기"
        self.assertEqual(sponsor.caption_text(ej), "#유료광고 오늘의 이야기")
        self.assertEqual(sponsor.caption_text({"caption": "x"}), "x")

    def test_export_caption_and_chips(self):
        self.set_ep(sponsored={"label": "광고", "cover_chip": True, "all_pages": True})
        self.ingest_all()
        self.full_letters()
        self.assertEqual(self.t("letter", "1")[0], 0)
        im = Image.open(self.pp(2, "lettered.png")).convert("RGB")
        self.assertEqual(im.getpixel((24 + 2, 24 + 20)), (0, 0, 0))  # 칩 테두리
        self.assertEqual(self.t("qa", "1")[0], 0)
        self.approve_all()
        code, o, e = self.t("export", "1")
        self.assertEqual(code, 0, e)
        with open(os.path.join(self.root, "episodes/ep01/out/caption.txt"), encoding="utf-8") as f:
            self.assertEqual(f.readline().strip(), "#광고")

    def test_chip_min_height(self):
        self.set_ep(sponsored={"label": "광고"})
        self.ingest_all()
        self.full_letters()
        self.t("letter", "1")
        im = Image.open(self.pp(1, "lettered.png")).convert("RGB")
        self.assertEqual(im.getpixel((24 + 2, 24 + 40)), (0, 0, 0))
        body = Image.open(self.pp(2, "lettered.png")).convert("RGB")
        self.assertNotEqual(body.getpixel((24 + 2, 24 + 40)), (0, 0, 0))  # all_pages 기본 false

    def test_forbidden_wording(self):
        for label, cap in (("AD", ""), ("광고", "Sponsored by x"), ("브랜드×작가", ""), ("체험단", ""),
                           ("광고", "#PR 후기"), ("광고", "브랜드 x 작가")):
            errs = sponsor.check({"format": "ranking", "caption": cap, "sponsored": {"label": label}})
            self.assertTrue(errs, (label, cap))
        self.assertEqual(sponsor.check({"format": "ranking", "caption": "후기", "sponsored": {"label": "상품 협찬"}}), [])
        self.assertEqual(sponsor.check({"format": "ranking", "caption": "협찬받음 브랜드x", "sponsored": {"label": "광고"}}), [])

    def test_qa_flags_bad_label(self):
        self.set_ep(sponsored={"label": "체험단"})
        self.ingest_all()
        self.full_letters()
        self.t("letter", "1")
        code, o, e = self.t("qa", "1")
        self.assertEqual(code, 1)
        self.assertIn("체험단", o)

    def test_sponsored_format_without_setting_is_error(self):
        self.set_ep(format="sponsored")
        self.ingest_all()
        self.full_letters()
        self.t("letter", "1")
        code, o, e = self.t("qa", "1")
        self.assertEqual(code, 1)
        self.assertIn("광고 표기 설정 필요", o)
        code, o, e = self.t("export", "1", "--force")
        self.assertEqual(code, 2)
        self.assertIn("광고 표기 설정 필요", e)


if __name__ == "__main__":
    unittest.main()

