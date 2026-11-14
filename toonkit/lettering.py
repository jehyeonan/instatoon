"""장 단위 식자: 표지/엔딩 자동 문구 + 본문 풍선."""
import os

from PIL import Image, ImageDraw

from . import balloons, textfit
from . import schema
from .util import ToonError, parse_color, read_json, write_json


def sb_page(sb, n):
    for p in sb.get("pages") or []:
        if p.get("n") == n:
            return p
    raise ToonError("storyboard.json 에 %d장이 없습니다." % n)


def load_letter(proj, ep, n):
    p = os.path.join(proj.page_dir(ep, n), "letter.json")
    if not os.path.isfile(p):
        return {"balloons": []}
    letter = read_json(p)
    errs = schema.check_letter(letter)
    if errs:
        raise ToonError("%d장 letter.json 오류:\n  " % n + "\n  ".join(errs))
    return letter


def plan_balloons(proj, ep, n, W, H):
    """letter.json 의 풍선을 계획한다. (plans, issues)"""
    sb = proj.load_storyboard(ep)
    page = sb_page(sb, n)
    lines = dict((ln["id"], ln) for ln in page.get("lines") or [])
    letter = load_letter(proj, ep, n)
    plans, issues = [], []
    for b in letter.get("balloons") or []:
        ln = lines.get(b.get("line"))
        if ln is None:
            issues.append("letter.json: 대사 id '%s' 가 storyboard 에 없습니다." % b.get("line"))
            continue
        spec = dict(b)
        spec["kind"] = b.get("kind") or ln.get("kind") or "speech"
        pl = balloons.plan(proj, spec, b.get("text", ln["text"]), W, H)
        pl["line"] = b["line"]
        plans.append(pl)
    return plans, issues


def _cover_size(proj, lines, area_px):
    x0, y0, x1, y1 = area_px
    aw, ah = x1 - x0, y1 - y0
    fp = proj.font("title")
    sizes = []
    for t in lines:
        size = int(ah / 3.0)
        while size > 10:
            f = textfit.load_font(fp, size)
            if f.getlength(t) + 2 * size * 0.09 <= aw:
                break
            size -= 1
        sizes.append(size)
    size = min(sizes)
    while size > 10 and size * 3 + size * 0.15 * 2 > ah:
        size -= 1
    return fp, size


def draw_cover(proj, img, page, n, ep):
    W, H = img.size
    cv = proj.series.get("cover") or {}
    lines = page.get("cover_title") or cv.get("title_lines")
    if not lines or len(lines) != 3:
        raise ToonError("%d장 표지: cover_title 3줄이 필요합니다(storyboard 또는 series.cover.title_lines)." % n)
    area = cv.get("title_area") or [0.05, 0.03, 0.95, 0.38]
    area_px = [area[0] * W, area[1] * H, area[2] * W, area[3] * H]
    accent_idx = int(cv.get("accent_line", 2)) - 1
    accent = parse_color(cv.get("accent_color"), "#E02020", "cover.accent_color")
    text_c = parse_color(cv.get("text_color"), "#111111", "cover.text_color")
    stroke_c = parse_color(cv.get("stroke_color"), "#111111", "cover.stroke_color")
    fp, size = _cover_size(proj, lines, area_px)
    font = textfit.load_font(fp, size)
    gap = size * 0.15
    total = size * 3 + gap * 2
    top = area_px[1] + ((area_px[3] - area_px[1]) - total) / 2.0
    cx = (area_px[0] + area_px[2]) / 2.0
    d = ImageDraw.Draw(img)
    sw = max(2, int(size * 0.09))
    for i, t in enumerate(lines):
        cy = top + size / 2.0 + i * (size + gap)
        if i == accent_idx:
            d.text((cx, cy), t, font=font, fill=accent, anchor="mm", stroke_width=sw, stroke_fill=stroke_c)
        else:
            d.text((cx, cy), t, font=font, fill=text_c, anchor="mm", stroke_width=max(2, sw // 2), stroke_fill=(255, 255, 255))
    draw_label(proj, img, ep)


def draw_label(proj, img, ep):
    W, H = img.size
    tpl = (proj.series.get("cover") or {}).get("label_template")
    if not tpl:
        return
    text = tpl.replace("{n}", str(ep))
    scale = W / 1080.0
    font = textfit.load_font(proj.font("caption"), max(int(34 * scale), 8))
    d = ImageDraw.Draw(img)
    bw = font.getlength(text) + 44 * scale
    bh = font.size + 28 * scale
    x1, y1 = W - 24 * scale, H - 24 * scale
    d.rectangle([x1 - bw, y1 - bh, x1, y1], fill=(17, 17, 17))
    d.text((x1 - bw / 2.0, y1 - bh / 2.0), text, font=font, fill=(255, 255, 255), anchor="mm")


def draw_ending(proj, img):
    W, H = img.size
    e = proj.series.get("ending") or {}
    area = e.get("area") or [0.08, 0.68, 0.92, 0.96]
    x0, y0, x1, y1 = area[0] * W, area[1] * H, area[2] * W, area[3] * H
    aw, ah = x1 - x0, y1 - y0
    scale = W / 1080.0
    d = ImageDraw.Draw(img)
    cx = (x0 + x1) / 2.0
    rows = []
    if e.get("series_line"):
        rows.append(("series", e["series_line"], "title", 0.30))
    if e.get("tagline"):
        rows.append(("tag", e["tagline"], "caption", 0.30))
    if e.get("follow_text"):
        rows.append(("follow", e["follow_text"], "title", 0.40))
    tot = sum(r[3] for r in rows) or 1.0
    y = y0
    for kind, t, role, frac in rows:
        rh = ah * frac / tot
        fit = textfit.fit_text(t, proj.font(role), aw * (0.7 if kind == "follow" else 0.95), rh * 0.62, 70 * scale, 20 * scale)
        font = textfit.load_font(proj.font(role), fit.size)
        cy = y + rh / 2.0
        stroke = 0
        if kind == "follow":
            tw = max(font.getlength(l) for l in fit.lines)
            bw, bh = tw + 60 * scale, fit.size * 1.3 * len(fit.lines) + 20 * scale
            d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], radius=bh / 2, fill=(17, 17, 17))
            fill = (255, 255, 255)
        elif kind == "series":
            accent = parse_color((proj.series.get("cover") or {}).get("accent_color"), "#E02020", "cover.accent_color")
            fill, stroke = accent, max(2, int(fit.size * 0.08))
        else:
            fill = (17, 17, 17)
        top = cy - (len(fit.lines) - 1) * fit.line_height / 2.0
        for i, line in enumerate(fit.lines):
            kw = dict(font=font, fill=fill, anchor="mm")
            if stroke:
                kw.update(stroke_width=stroke, stroke_fill=(255, 255, 255))
            d.text((cx, top + i * fit.line_height), line, **kw)
        y += rh


def render_page(proj, ep, n):
    """lettered.png 를 만들고 보고 dict 를 돌려준다."""
    v, src = proj.require_usable(ep, n)
    img = Image.open(src).convert("RGB")
    W, H = img.size
    page = sb_page(proj.load_storyboard(ep), n)
    plans, issues = plan_balloons(proj, ep, n, W, H)
    if page.get("kind") == "cover":
        draw_cover(proj, img, page, n, ep)
    elif page.get("kind") == "ending":
        draw_ending(proj, img)
    overflow = []
    for pl in plans:
        if pl["fit"].overflow:
            overflow.append(pl["line"])
        balloons.render(img, pl)
    meta = os.path.join(proj.page_dir(ep, n), "lettered.json")
    if os.path.isfile(meta):
        os.remove(meta)  # 저장 도중 끊겨도 옛 메타가 최신으로 보이지 않게
    img.save(os.path.join(proj.page_dir(ep, n), "lettered.png"))
    rep = {"version": v, "source": os.path.relpath(src, proj.root), "size": [W, H],
           "overflow": overflow, "issues": issues, "balloons": len(plans)}
    write_json(meta, rep)
    return rep


def draw_grid(proj, ep, n):
    v, src = proj.require_usable(ep, n)
    img = Image.open(src).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img, "RGBA")
    font = textfit.load_font(proj.font("caption"), max(int(W / 45), 10))
    lw = max(1, W // 700)
    for i in range(1, 10):
        x, y = W * i / 10.0, H * i / 10.0
        d.line([(x, 0), (x, H)], fill=(255, 0, 255, 150), width=lw)
        d.line([(0, y), (W, y)], fill=(0, 160, 255, 150), width=lw)
        lab = "%.1f" % (i / 10.0)
        d.text((x + 3, 3), lab, font=font, fill=(200, 0, 200, 255))
        d.text((3, y + 3), lab, font=font, fill=(0, 110, 200, 255))
    out = os.path.join(proj.page_dir(ep, n), "grid.png")
    img.save(out)
    return out

