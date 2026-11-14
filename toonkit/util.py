import datetime
import json
import os
import re

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(SKILL_DIR, "fonts")


class ToonError(Exception):
    """사용자에게 그대로 보여 줄 오류."""


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ToonError("파일이 없습니다: %s" % path)
    except ValueError as e:
        raise ToonError("JSON 형식 오류 %s: %s" % (path, e))


def write_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _num(x, what):
    m = re.search(r"\d+", str(x))
    if not m:
        raise ToonError("%s 번호를 읽을 수 없습니다: %s" % (what, x))
    return int(m.group(0))


def norm_ep(x):
    return _num(x, "에피소드")


def norm_page(x):
    return _num(x, "장")


def norm_text(s):
    """대사 비교용 정규화: 공백 제거, ... 와 … 동일시."""
    s = str(s).replace("...", "…").replace("⋯", "…")
    return re.sub(r"\s+", "", s)


# 4:5 세로. ingest 거부, qa, export 가 모두 이 범위를 쓴다(export 는 이 범위 안에서 중앙 크롭).
RATIO_MIN, RATIO_MAX = 0.78, 0.82

ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def check_id(x, what="id"):
    if not isinstance(x, str) or not ID_RE.match(x):
        raise ToonError("%s '%s' 는 영문, 숫자, _, - 만 쓸 수 있습니다." % (what, x))
    return x


def parse_color(c, default, what="색상"):
    c = default if c is None else c
    if not isinstance(c, str) or not re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", c):
        raise ToonError("%s '%s' 는 #RGB 또는 #RRGGBB 형식이어야 합니다." % (what, c))
    h = c[1:]
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def crop_box(w, h, cw, ch):
    """export 가 쓰는 중앙 크롭 영역 (x0, y0, x1, y1)."""
    target = cw / float(ch)
    r = w / float(h)
    if r > target:
        nw = int(round(h * target))
        x = (w - nw) // 2
        return (x, 0, x + nw, h)
    if r < target:
        nh = int(round(w / target))
        y = (h - nh) // 2
        return (0, y, w, y + nh)
    return (0, 0, w, h)


def verify_image(path):
    """열 수 있는 이미지인지 확인한다. 실패하면 ToonError."""
    from PIL import Image
    try:
        with Image.open(path) as im:
            im.verify()
    except Exception as e:
        raise ToonError("이미지 파일이 아니거나 손상됐습니다: %s (%s)" % (path, e.__class__.__name__))


def find_root(start=None, explicit=False):
    if explicit:
        d = os.path.abspath(start)
        if not os.path.isfile(os.path.join(d, "series.json")):
            raise ToonError("--root 폴더에 series.json 이 없습니다: %s" % d)
        return d
    cur = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(cur, "series.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise ToonError("series.json을 찾을 수 없습니다. toon init 으로 시리즈 폴더를 만들거나 --root 를 지정하세요.")
        cur = parent

