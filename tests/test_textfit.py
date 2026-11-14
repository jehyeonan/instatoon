import os
import unittest

import helpers  # noqa: F401
from toonkit import textfit
from toonkit.util import FONT_DIR

FONT = os.path.join(FONT_DIR, "Pretendard-Bold.otf")


class TextFitTests(unittest.TestCase):
    def test_wrap_on_word_boundaries(self):
        f = textfit.load_font(FONT, 40)
        lines = textfit.wrap("그럼 이제 AI가 강사님 대체하는 거 아니에요?", f, 260)
        self.assertGreater(len(lines), 1)
        for l in lines:
            self.assertLessEqual(f.getlength(l), 260.5)
        self.assertEqual("".join(lines).replace(" ", ""), "그럼이제AI가강사님대체하는거아니에요?")

    def test_long_word_split_by_char(self):
        f = textfit.load_font(FONT, 40)
        lines = textfit.wrap("가나다라마바사아자차카타파하" * 3, f, 200)
        self.assertGreater(len(lines), 2)
        for l in lines:
            self.assertLessEqual(f.getlength(l), 200.5)

    def test_balance_avoids_short_last_line(self):
        f = textfit.load_font(FONT, 40)
        text = "혹시 모르니까 검색해 볼까"
        greedy = textfit.wrap(text, f, 330)
        balanced = textfit.balance(text, f, 330, greedy)
        self.assertEqual(len(balanced), len(greedy))
        widest = lambda ls: max(f.getlength(l) for l in ls)
        self.assertLessEqual(widest(balanced), widest(greedy))
        self.assertEqual(" ".join(balanced), text)

    def test_fit_shrinks_and_fits_box(self):
        fit = textfit.fit_text("이 문장은 꽤 길어서 박스 안에 맞추려면 글자가 줄어야 합니다", FONT, 300, 120, 60, 20)
        self.assertFalse(fit.overflow)
        self.assertLess(fit.size, 60)
        f = textfit.load_font(FONT, fit.size)
        w, h = textfit.block_size(fit.lines, f, fit.size, fit.spacing)
        self.assertLessEqual(w, 300.5)
        self.assertLessEqual(h, 120.5)

    def test_overflow_reported(self):
        fit = textfit.fit_text("아주 긴 문장입니다 " * 20, FONT, 120, 50, 40, 30)
        self.assertTrue(fit.overflow)
        self.assertEqual(fit.size, 30)

    def test_short_text_keeps_max_size(self):
        fit = textfit.fit_text("쿵", FONT, 300, 120, 48, 20)
        self.assertEqual(fit.size, 48)
        self.assertEqual(fit.lines, ["쿵"])


if __name__ == "__main__":
    unittest.main()

