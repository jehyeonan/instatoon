import os
import re
import shutil

from PIL import Image

from . import schema, sponsor
from .util import RATIO_MAX, RATIO_MIN, ToonError, crop_box

# out/ 안에서 export 가 만들고 교체하는 파일은 NN.jpg, preview.jpg, caption.txt 뿐이다.
# 그 밖의 파일은 건드리지 않는다. 모든 장을 검증하고 out.tmp 에 다 만든 뒤에만 out/ 을 바꾼다.
OWN_RE = re.compile(r"^(\d\d\.jpg|preview\.jpg|caption\.txt)$")


def _check_ratio(path, n):
    with Image.open(path) as im:
        w, h = im.size
    r = w / float(h)
    if not (RATIO_MIN <= r <= RATIO_MAX):
        return "%d장: 비율 %.3f 은 내보내기 허용 범위 %.2f~%.2f 밖입니다. 이미지를 다시 생성하세요." % (n, r, RATIO_MIN, RATIO_MAX)
    return None


def _fit_to_canvas(src, cw, ch):
    im = Image.open(src).convert("RGB")
    im = im.crop(crop_box(im.size[0], im.size[1], cw, ch))
    return im.resize((cw, ch), Image.LANCZOS)


def _validate(proj, ep, pages, force):
    problems = list(schema.check_series(proj.series))
    problems += sponsor.check(proj.load_episode(ep))
    for p in pages:
        n = p["n"]
        pj = proj.page_json(ep, n)
        if not pj.get("approved") and not force:
            problems.append("%d장: 승인되지 않았습니다(toon approve)." % n)
        try:
            proj.require_usable(ep, n)
        except ToonError as e:
            problems.append(str(e))
            continue
        stale = proj.stale_problems(ep, n)
        problems += stale
        if not stale:
            r = _check_ratio(os.path.join(proj.page_dir(ep, n), "lettered.png"), n)
            if r:
                problems.append(r)
    if problems:
        raise ToonError("내보낼 수 없습니다:\n  " + "\n  ".join(problems))


def export(proj, ep, force=False):
    sb, _ = proj.valid_storyboard(ep)
    pages = sorted(sb["pages"], key=lambda p: p["n"])
    _validate(proj, ep, pages, force)
    epj = proj.load_episode(ep)
    cw, ch = proj.canvas
    out = os.path.join(proj.ep_dir(ep), "out")
    tmp = out + ".tmp"
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    try:
        imgs = []
        for i, p in enumerate(pages):
            im = _fit_to_canvas(os.path.join(proj.page_dir(ep, p["n"]), "lettered.png"), cw, ch)
            im.save(os.path.join(tmp, "%02d.jpg" % (i + 1)), quality=92)
            imgs.append(im)
        cols = 4
        rows = (len(imgs) + cols - 1) // cols
        tw = 400
        th = int(round(tw * ch / float(cw)))
        gap = 12
        sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), (235, 235, 235))
        for i, im in enumerate(imgs):
            x = gap + (i % cols) * (tw + gap)
            y = gap + (i // cols) * (th + gap)
            sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        sheet.save(os.path.join(tmp, "preview.jpg"), quality=88)
        cap = sponsor.caption_text(epj)
        tags = epj.get("hashtags") or []
        if isinstance(tags, str):
            tags = tags.split()
        tagline = " ".join(t if t.startswith("#") else "#" + t for t in tags)
        with open(os.path.join(tmp, "caption.txt"), "w", encoding="utf-8") as f:
            f.write(cap + ("\n\n" + tagline if tagline else "") + "\n")
        os.makedirs(out, exist_ok=True)
        new = set(os.listdir(tmp))
        for name in os.listdir(out):  # 이전 내보내기의 남은 NN.jpg 만 정리
            if OWN_RE.match(name) and name not in new:
                os.remove(os.path.join(out, name))
        for name in sorted(new):
            os.replace(os.path.join(tmp, name), os.path.join(out, name))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out, len(imgs)
