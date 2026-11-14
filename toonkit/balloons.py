"""말풍선 계획(plan)과 렌더(render). 좌표는 이미지 기준 0~1 비율."""
import math

from PIL import Image, ImageDraw, ImageFilter

from . import textfit
from .util import ToonError

SS = 2
INK = (17, 17, 17)
KINDS = ("speech", "thought", "narration", "shout", "sfx")
FONT_ROLE = {"speech": "dialogue", "thought": "dialogue", "narration": "caption",
             "shout": "title", "sfx": "title"}


def plan(proj, spec, text, W, H):
    kind = spec.get("kind") or "speech"
    if kind not in KINDS:
        raise ToonError("알 수 없는 풍선 종류: %s" % kind)
    scale = W / 1080.0
    x0, y0, x1, y1 = spec["box"]
    box = [x0 * W, y0 * H, x1 * W, y1 * H]
    bw, bh = box[2] - box[0], box[3] - box[1]
    sw = 3.0 * scale
    if kind == "speech":
        shape = "ellipse" if bw / bh < 2.2 else "rrect"
    else:
        shape = {"thought": "cloud", "narration": "rect", "shout": "star", "sfx": "none"}[kind]
    if shape in ("ellipse", "cloud"):
        tw, th = bw * 0.74 - 2 * sw, bh * 0.70 - 2 * sw
    elif shape == "rrect":
        tw = bw - 2 * max(0.05 * bw, 10 * scale) - 2 * sw
        th = bh - 2 * max(0.12 * bh, 8 * scale) - 2 * sw
    elif shape == "rect":
        tw, th = bw - 24 * scale - 2 * sw, bh - 18 * scale - 2 * sw
    elif shape == "star":
        tw, th = bw * 0.62, bh * 0.58
    else:
        tw, th = bw * 0.88, bh * 0.88
    if spec.get("font_size"):
        max_size = float(spec["font_size"]) * scale
    elif kind == "sfx":
        max_size = min(th, 200 * scale)
    else:
        max_size = (54 if kind == "shout" else 48) * scale
    min_size = (30 if kind == "sfx" else 26) * scale
    fp = proj.font(FONT_ROLE[kind])
    fit = textfit.fit_text(text, fp, max(tw, 1), max(th, 1), max_size, min_size)
    tail = None
    if spec.get("tail") and kind in ("speech", "thought", "shout"):
        tail = [spec["tail"][0] * W, spec["tail"][1] * H]
    return {"kind": kind, "shape": shape, "box": box, "tail": tail, "fit": fit,
            "fontpath": fp, "scale": scale, "sw": sw, "text": text}


def _tail_geom(pl):
    """꼬리 기하: 삼각형 점 3개 또는 생각풍선 원 3개. 꼬리가 없으면 None."""
    t = pl["tail"]
    if not t:
        return None
    x0, y0, x1, y1 = pl["box"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    a, b = (x1 - x0) / 2.0, (y1 - y0) / 2.0
    dx, dy = t[0] - cx, t[1] - cy
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return None
    ux, uy = dx / dist, dy / dist
    rb = 1.0 / math.sqrt((ux / a) ** 2 + (uy / b) ** 2)
    if dist <= rb * 1.02:
        return None
    m = min(x1 - x0, y1 - y0)
    if pl["kind"] == "thought":
        e = (cx + ux * rb, cy + uy * rb)
        d = dist - rb
        circles = []
        for f, r in ((0.22, 0.075), (0.55, 0.055), (0.9, 0.04)):
            circles.append((e[0] + ux * d * f, e[1] + uy * d * f, max(m * r, 3 * pl["scale"])))
        return {"circles": circles}
    bc = (cx + ux * rb * 0.85, cy + uy * rb * 0.85)
    hw = max(0.12 * m, 9 * pl["scale"])
    px, py = -uy, ux
    return {"tri": [(bc[0] + px * hw, bc[1] + py * hw), (bc[0] - px * hw, bc[1] - py * hw), (t[0], t[1])]}


def _body(d, pl, P):
    x0, y0, x1, y1 = pl["box"]
    shape = pl["shape"]
    if shape == "ellipse":
        d.ellipse([P(x0, y0), P(x1, y1)], fill=255)
    elif shape == "rrect":
        d.rounded_rectangle([P(x0, y0), P(x1, y1)], radius=(y1 - y0) * 0.45 * SS, fill=255)
    elif shape == "rect":
        d.rectangle([P(x0, y0), P(x1, y1)], fill=255)
    elif shape == "star":
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        a, b = (x1 - x0) / 2.0, (y1 - y0) / 2.0
        n = 18
        pts = []
        for i in range(n * 2):
            r = 1.0 if i % 2 == 0 else 0.8
            ang = math.pi * i / n - math.pi / 2
            pts.append(P(cx + a * r * math.cos(ang), cy + b * r * math.sin(ang)))
        d.polygon(pts, fill=255)
    elif shape == "cloud":
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        m = min(x1 - x0, y1 - y0)
        r = 0.14 * m
        a, b = (x1 - x0) / 2.0 - r, (y1 - y0) / 2.0 - r
        d.ellipse([P(cx - a, cy - b), P(cx + a, cy + b)], fill=255)
        n = max(10, int(2 * math.pi * max(a, b) / (1.5 * r)))
        for i in range(n):
            ang = 2 * math.pi * i / n
            px, py = cx + a * math.cos(ang), cy + b * math.sin(ang)
            d.ellipse([P(px - r, py - r), P(px + r, py + r)], fill=255)


def bounds(pl):
    """풍선이 칠하는 영역의 바깥 경계(px)."""
    x0, y0, x1, y1 = pl["box"]
    xs, ys = [x0, x1], [y0, y1]
    g = _tail_geom(pl)
    if g and "tri" in g:
        for p in g["tri"]:
            xs.append(p[0])
            ys.append(p[1])
    if g and "circles" in g:
        for c in g["circles"]:
            xs += [c[0] - c[2], c[0] + c[2]]
            ys += [c[1] - c[2], c[1] + c[2]]
    m = pl["sw"] * 2 + 4
    return [min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m]


def render(img, pl):
    """img(RGB)에 풍선과 글자를 그린다. 몸체+꼬리를 한 마스크로 합쳐 외곽선 이음매가 없다."""
    if pl["shape"] != "none":
        bx0, by0, bx1, by1 = bounds(pl)
        ox, oy = int(math.floor(bx0)), int(math.floor(by0))
        pw, ph = int(math.ceil(bx1)) - ox, int(math.ceil(by1)) - oy

        def P(x, y):
            return ((x - ox) * SS, (y - oy) * SS)

        mask = Image.new("L", (pw * SS, ph * SS), 0)
        d = ImageDraw.Draw(mask)
        _body(d, pl, P)
        g = _tail_geom(pl)
        if g and "tri" in g:
            d.polygon([P(*p) for p in g["tri"]], fill=255)
        if g and "circles" in g:
            for cx, cy, r in g["circles"]:
                d.ellipse([P(cx - r, cy - r), P(cx + r, cy + r)], fill=255)
        k = 2 * int(round(pl["sw"] * SS)) + 1
        outline = mask.filter(ImageFilter.MaxFilter(k))
        layer = Image.new("RGBA", mask.size, (0, 0, 0, 0))
        layer.paste((0, 0, 0, 255), mask=outline)
        layer.paste((255, 255, 255, 255), mask=mask)
        small = layer.resize((pw, ph), Image.LANCZOS)
        img.paste(small.convert("RGB"), (ox, oy), small.getchannel("A"))
    draw_text(img, pl)


def draw_text(img, pl):
    fit = pl["fit"]
    x0, y0, x1, y1 = pl["box"]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    font = textfit.load_font(pl["fontpath"], fit.size)
    d = ImageDraw.Draw(img)
    lh = fit.line_height
    top = cy - (len(fit.lines) - 1) * lh / 2.0
    for i, line in enumerate(fit.lines):
        xy = (cx, top + i * lh)
        if pl["kind"] == "sfx":
            d.text(xy, line, font=font, fill=INK, anchor="mm",
                   stroke_width=max(2, int(fit.size * 0.1)), stroke_fill=(255, 255, 255))
        else:
            d.text(xy, line, font=font, fill=INK, anchor="mm")

