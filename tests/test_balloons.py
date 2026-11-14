import unittest

import helpers  # noqa: F401
from PIL import Image

from toonkit import balloons
from toonkit.project import Project

import os
import shutil


class BalloonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir, cls.root = helpers.temp_series()
        cls.proj = Project(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _render(self, kind, box, tail=None, text="안녕하세요 이건 테스트 대사입니다"):
        W, H = 1122, 1402
        img = Image.new("RGB", (W, H), (255, 255, 255))
        spec = {"kind": kind, "box": box}
        if tail:
            spec["tail"] = tail
        pl = balloons.plan(self.proj, spec, text, W, H)
        balloons.render(img, pl)
        return img, pl

    def _changed_bbox(self, img):
        diff = Image.eval(img.convert("L"), lambda p: 255 if p < 250 else 0)
        return diff.getbbox()

    def test_every_kind_renders_inside_bounds(self):
        cases = [("speech", [0.1, 0.1, 0.5, 0.25], [0.3, 0.4]),
                 ("speech", [0.1, 0.1, 0.8, 0.2], [0.5, 0.3]),
                 ("thought", [0.1, 0.1, 0.5, 0.3], [0.3, 0.45]),
                 ("narration", [0.1, 0.1, 0.6, 0.18], None),
                 ("shout", [0.2, 0.2, 0.8, 0.45], [0.5, 0.6]),
                 ("sfx", [0.2, 0.2, 0.7, 0.35], None)]
        for kind, box, tail in cases:
            img, pl = self._render(kind, box, tail)
            self.assertFalse(pl["fit"].overflow, kind)
            bb = self._changed_bbox(img)
            self.assertIsNotNone(bb, kind)
            bd = balloons.bounds(pl)
            self.assertGreaterEqual(bb[0], bd[0] - 1, kind)
            self.assertGreaterEqual(bb[1], bd[1] - 1, kind)
            self.assertLessEqual(bb[2], bd[2] + 1, kind)
            self.assertLessEqual(bb[3], bd[3] + 1, kind)

    def test_speech_stays_within_box_without_tail(self):
        img, pl = self._render("speech", [0.2, 0.2, 0.6, 0.35])
        bb = self._changed_bbox(img)
        x0, y0, x1, y1 = pl["box"]
        m = pl["sw"] * 2 + 2
        self.assertGreaterEqual(bb[0], x0 - m)
        self.assertLessEqual(bb[2], x1 + m)
        self.assertGreaterEqual(bb[1], y0 - m)
        self.assertLessEqual(bb[3], y1 + m)

    def test_tail_extends_to_target(self):
        img, pl = self._render("speech", [0.2, 0.1, 0.6, 0.25], [0.4, 0.5])
        bb = self._changed_bbox(img)
        self.assertGreater(bb[3], 0.45 * 1402)

    def test_tail_no_seam(self):
        # 꼬리와 몸체의 접합부 근처에 외곽선 안쪽 흰 픽셀이 이어져 있어야 한다(이음매 선 없음).
        img, pl = self._render("speech", [0.2, 0.1, 0.6, 0.25], [0.4, 0.5])
        x0, y0, x1, y1 = pl["box"]
        cx = (x0 + x1) / 2.0
        by = y1 - 8
        # 몸체 아래쪽 안쪽 한 줄에서, 꼬리 위치 부근은 검은 선이 없어야 한다.
        px = img.load()
        dark = [x for x in range(int(cx - 60), int(cx + 60)) if px[x, int(by)][0] < 100]
        self.assertEqual(dark, [])

    def test_text_is_drawn_dark_pixels_inside(self):
        img, pl = self._render("narration", [0.1, 0.1, 0.6, 0.2], None, text="그날 밤")
        x0, y0, x1, y1 = [int(v) for v in pl["box"]]
        inner = img.crop((x0 + 12, y0 + 12, x1 - 12, y1 - 12)).convert("L")
        self.assertIsNotNone(Image.eval(inner, lambda p: 255 if p < 100 else 0).getbbox())


if __name__ == "__main__":
    unittest.main()

