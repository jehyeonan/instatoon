"""장 단위 식자: 표지/엔딩 자동 문구 + 본문 풍선."""
import os

from PIL import Image, ImageDraw

from . import balloons, formats, sponsor, textfit
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


def draw_cover(proj, img, page, n, ep, ad_label=None):
    W, H = img.size
    cv = proj.series.get("cover") or {}
    lines = page.get("cover_title") or cv.get("title_lines")
    if not lines or len(lines) != 3:
        raise ToonError("%d장 표지: cover_title 3줄이 필요합니다(storyboard 또는 series.cover.title_lines)." % n)
    area = cv.get("title_area") or [0.05, 0.03, 0.95, 0.38]
    area_px = [area[0] * W, area[1] * H, area[2] * W, area[3] * H]
    scale = W / 1080.0
    if ad_label:
        # 좌상단 광고 칩 아래에서 제목을 시작한다(칩과 제목 겹침 방지)
        area_px[1] = max(area_px[1], ad_chip_box(proj, W, H, ad_label)[3] + 12 * scale)
    sub_text = page.get("cover_subtitle")
    sub_box = None
    if sub_text:
        # 부제 칩을 제목 영역 맨 아래 안쪽에 두고, 제목은 그 위 공간에 맞춘다(캐릭터 머리 침범 방지)
        probe = subtitle_chip_box(proj, W, H, sub_text, 0)
        ch = probe[3] - probe[1]
        sub_top = area_px[3] - ch
        sub_box = subtitle_chip_box(proj, W, H, sub_text, sub_top - 14 * scale)
        area_px[3] = sub_top - 14 * scale
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
    if sub_box:
        x0, y0, x1, y1, sfont = sub_box
        d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 4.0, fill=accent)
        d.text(((x0 + x1) / 2.0, (y0 + y1) / 2.0), sub_text, font=sfont, fill=(255, 255, 255), anchor="mm")
    if page.get("cover_note"):
        draw_cover_note(proj, img, page["cover_note"])


def subtitle_chip_box(proj, W, H, text, top):
    """표지 부제 칩의 (x0, y0, x1, y1, font). 제목 영역 아래(top) 가운데에 놓고 캔버스 안으로 맞춘다."""
    scale = W / 1080.0
    size = 44 * scale
    padx, pady = 36 * scale, 16 * scale
    maxw = W * 0.9 - 2 * padx
    while size > 12 and textfit.load_font(proj.font("title"), int(size)).getlength(text) > maxw:
        size -= 1
    font = textfit.load_font(proj.font("title"), int(size))
    bw = font.getlength(text) + 2 * padx
    bh = font.size * 1.25 + 2 * pady
    x0 = (W - bw) / 2.0
    y0 = min(top + 14 * scale, H - bh - 24 * scale)
    return (x0, y0, x0 + bw, y0 + bh, font)


def draw_subtitle_chip(proj, img, text, top, accent):
    W, H = img.size
    x0, y0, x1, y1, font = subtitle_chip_box(proj, W, H, text, top)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) / 4.0, fill=accent)
    d.text(((x0 + x1) / 2.0, (y0 + y1) / 2.0), text, font=font, fill=(255, 255, 255), anchor="mm")


def draw_cover_note(proj, img, text):
    """표지 맨 아래 왼쪽의 작은 회색 고지문(오른쪽 아래 화 번호 라벨을 피해 가로 절반 안)."""
    W, H = img.size
    scale = W / 1080.0
    size = 28 * scale
    maxw = W * 0.5
    while size > 8 and textfit.load_font(proj.font("caption"), int(size)).getlength(text) > maxw:
        size -= 1
    font = textfit.load_font(proj.font("caption"), int(size))
    d = ImageDraw.Draw(img)
    d.text((24 * scale, H - 24 * scale), text, font=font, fill=(120, 120, 120), anchor="ls",
           stroke_width=max(1, int(scale * 2)), stroke_fill=(255, 255, 255))


def ad_chip_box(proj, W, H, label):
    scale = W / 1080.0
    font = textfit.load_font(proj.font("title"), max(int(32 * scale), 8))
    bw = font.getlength(label) + 40 * scale
    bh = max(48 * scale, font.size * 1.5)
    x0, y0 = 24 * scale, 24 * scale
    return (x0, y0, x0 + bw, y0 + bh, font)


def draw_ad_chip(proj, img, label):
    """좌상단 광고 칩: 흰 바탕, 검정 굵은 테두리와 글씨. 1080 기준 높이 48px 이상."""
    W, H = img.size
    scale = W / 1080.0
    x0, y0, x1, y1, font = ad_chip_box(proj, W, H, label)
    bw, bh = x1 - x0, y1 - y0
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], fill=(255, 255, 255), outline=(0, 0, 0), width=max(2, int(4 * scale)))
    d.text((x0 + bw / 2.0, y0 + bh / 2.0), label, font=font, fill=(0, 0, 0), anchor="mm")
    return (x0, y0, x0 + bw, y0 + bh)


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


def ending_mode(epj):
    """엔딩 장 표기: 'series'(시리즈 엔딩) 또는 'continue'(- 계속 -)."""
    if epj.get("final"):
        return "series"
    mode = epj.get("ending")
    if mode in ("series", "continue"):
        return mode
    f = formats.get(epj.get("format"))
    return "continue" if f and f["ending_type"] == "continue" else "series"


def draw_continue(proj, img, text):
    W, H = img.size
    scale = W / 1080.0
    size = 52 * scale
    font = textfit.load_font(proj.font("title"), int(size))
    while size > 12 and font.getlength(text) > W * 0.8:
        size -= 1
        font = textfit.load_font(proj.font("title"), int(size))
    d = ImageDraw.Draw(img)
    d.text((W / 2.0, H - 70 * scale), text, font=font, fill=(17, 17, 17), anchor="mm",
           stroke_width=max(2, int(size * 0.08)), stroke_fill=(255, 255, 255))


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
    epj = proj.load_episode(ep)
    sp = sponsor.settings(epj)
    if page.get("kind") == "cover":
        draw_cover(proj, img, page, n, ep, ad_label=sp["label"] if sp and (sp["cover_chip"] or sp["all_pages"]) else None)
    elif page.get("kind") == "ending":
        if ending_mode(epj) == "continue":
            draw_continue(proj, img, epj.get("continue_text") or "- 계속 -")
        else:
            draw_ending(proj, img)
    if sp and ((page.get("kind") == "cover" and sp["cover_chip"]) or sp["all_pages"]):
        draw_ad_chip(proj, img, sp["label"])
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

