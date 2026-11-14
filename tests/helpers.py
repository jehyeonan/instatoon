import contextlib
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)

from PIL import Image, ImageDraw  # noqa: E402

from toonkit import cli  # noqa: E402

EXAMPLE = os.path.join(SKILL, "examples", "yunseo")


def toon(*argv):
    """cli.main 을 호출해 (종료코드, 표준출력, 표준오류) 를 돌려준다."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as e:
            code = e.code or 0
    return code, out.getvalue(), err.getvalue()


def make_image(path, size=(1122, 1402)):
    im = Image.new("RGB", size, (250, 250, 250))
    d = ImageDraw.Draw(im)
    d.ellipse([size[0] * 0.3, size[1] * 0.5, size[0] * 0.7, size[1] * 0.9], outline=(0, 0, 0), width=6)
    im.save(path)
    return path


def temp_series():
    """예제 데이터를 복사한 임시 시리즈 폴더."""
    d = tempfile.mkdtemp(prefix="toontest_")
    root = os.path.join(d, "s")
    shutil.copytree(EXAMPLE, root)
    return d, root

