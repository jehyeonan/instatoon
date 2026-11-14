from PIL import ImageFont

_CACHE = {}


class Fit(object):
    def __init__(self, size, lines, overflow, spacing):
        self.size = size
        self.lines = lines
        self.overflow = overflow
        self.spacing = spacing

    @property
    def line_height(self):
        return self.size * self.spacing


def load_font(path, size):
    key = (path, int(size))
    if key not in _CACHE:
        _CACHE[key] = ImageFont.truetype(path, int(size))
    return _CACHE[key]


def split_long(word, font, max_w):
    """한 어절이 max_w 보다 길면 글자 단위로 쪼갠다."""
    parts, cur = [], ""
    for ch in word:
        if cur and font.getlength(cur + ch) > max_w:
            parts.append(cur)
            cur = ch
        else:
            cur += ch
    parts.append(cur)
    return parts


def wrap(text, font, max_w):
    """공백(어절) 기준 줄바꿈. 줄바꿈 문자는 그대로 존중."""
    lines = []
    for para in str(text).split("\n"):
        cur = ""
        for w in [x for x in para.split(" ") if x]:
            if font.getlength(w) > max_w:
                if cur:
                    lines.append(cur)
                    cur = ""
                parts = split_long(w, font, max_w)
                lines.extend(parts[:-1])
                cur = parts[-1]
                continue
            t = w if not cur else cur + " " + w
            if font.getlength(t) <= max_w:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def block_size(lines, font, size, spacing):
    w = max([font.getlength(l) for l in lines] or [0])
    h = size + (len(lines) - 1) * size * spacing
    return w, h


def balance(text, font, max_w, lines):
    """줄 수는 그대로 두고 가장 긴 줄이 최소가 되도록 줄 너비를 좁혀 다시 나눈다.

    "강사님, 질문 / 있습니다!" 처럼 마지막 줄만 짧게 남는 것을 막는다.
    """
    n = len(lines)
    if n < 2:
        return lines
    lo = max([font.getlength(w) for w in str(text).split() if w] or [0])
    lo = min(lo, max_w)
    hi = max_w
    best = lines
    for _ in range(14):
        if hi - lo < 1:
            break
        mid = (lo + hi) / 2.0
        cand = wrap(text, font, mid)
        if len(cand) <= n:
            best, hi = cand, mid
        else:
            lo = mid
    return best


def fit_text(text, fontpath, box_w, box_h, max_size, min_size, spacing=1.25):
    """max_size 부터 줄여 가며 박스 안에 맞춘다. min_size 에서도 안 맞으면 overflow=True."""
    max_size = max(int(max_size), 1)
    min_size = min(max(int(min_size), 1), max_size)
    size = max_size
    while True:
        font = load_font(fontpath, size)
        lines = wrap(text, font, box_w)
        w, h = block_size(lines, font, size, spacing)
        if w <= box_w + 0.5 and h <= box_h + 0.5:
            return Fit(size, balance(text, font, box_w, lines), False, spacing)
        if size <= min_size:
            return Fit(size, lines, True, spacing)
        size -= 1

