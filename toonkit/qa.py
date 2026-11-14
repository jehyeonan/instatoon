"""자동 검사. 시각 점검이 필요한 항목은 따로 목록으로 낸다."""
import os

from PIL import Image

from . import balloons, lettering, schema
from .util import RATIO_MAX, RATIO_MIN, crop_box, norm_text, read_json, write_json

VISUAL_ITEMS = [
    "캐릭터 속성이 시트와 같은가: {attrs}",
    "로고·브랜드 마크·상표(옷, 노트북, 화면)가 없는가",
    "허용 목록 밖의 글자가 그림에 없는가{allow}",
    "실존 인물을 닮은 얼굴이나 유명인 캐리커처가 없는가",
    "풍선·표지 제목이 얼굴과 핵심 소품을 가리지 않는가 (lettered.png 를 직접 볼 것)",
]


def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check_page(proj, ep, page):
    n = page["n"]
    errors, warns = [], []
    v, src = proj.chosen_file(ep, n)
    pj = proj.page_json(ep, n)
    size = None
    if not src or not os.path.isfile(src):
        errors.append("채택할 이미지 버전이 없습니다. " + proj.no_image_hint(ep, n))
    elif any(x["v"] == v and x.get("rejected") for x in pj.get("versions") or []):
        errors.append("채택된 v%s 는 rejected 입니다. toon ingest 로 새 버전을 등록하세요." % v)
    else:
        with Image.open(src) as im:
            size = im.size
        r = size[0] / float(size[1])
        if not (RATIO_MIN <= r <= RATIO_MAX):
            errors.append("이미지 비율 %.3f (가로 x세로 = %dx%d): 세로 4:5(%.2f~%.2f)가 아닙니다." % (r, size[0], size[1], RATIO_MIN, RATIO_MAX))
    # 대사 일치·누락
    lines = dict((ln["id"], ln) for ln in page.get("lines") or [])
    lp = os.path.join(proj.page_dir(ep, n), "letter.json")
    letter = {"balloons": []}
    has_letter = os.path.isfile(lp)
    lerrs = []
    if has_letter:
        raw = read_json(lp)
        lerrs = schema.check_letter(raw)
        errors += ["letter.json: " + e for e in lerrs]
        if not lerrs:
            letter = raw
    elif lines:
        errors.append("letter.json 이 없습니다(대사 %d개 미식자)." % len(lines))
    seen = set()
    for b in letter.get("balloons") or []:
        lid = b.get("line")
        if lid not in lines:
            errors.append("letter.json: 대사 id '%s' 가 storyboard 에 없습니다." % lid)
            continue
        if lid in seen:
            warns.append("대사 '%s' 풍선이 중복입니다." % lid)
        seen.add(lid)
        if "text" in b and norm_text(b["text"]) != norm_text(lines[lid]["text"]):
            errors.append("대사 '%s' 문구가 storyboard 와 다릅니다: %r != %r" % (lid, b["text"], lines[lid]["text"]))
    for lid in lines:
        if lid not in seen and has_letter:
            errors.append("대사 '%s' 가 letter.json 에서 빠졌습니다." % lid)
    # 넘침, 캔버스 밖, 겹침
    if size and not lerrs:
        plans, issues = lettering.plan_balloons(proj, ep, n, size[0], size[1])
        cb = crop_box(size[0], size[1], *proj.canvas)
        rects = []
        for pl in plans:
            if pl["fit"].overflow:
                errors.append("대사 '%s' 글자가 박스를 넘칩니다(최소 크기 미만). 박스를 키우거나 대사를 줄이세요." % pl["line"])
            bd = balloons.bounds(pl)
            if bd[0] < 0 or bd[1] < 0 or bd[2] > size[0] or bd[3] > size[1]:
                errors.append("대사 '%s' 풍선(꼬리 포함)이 캔버스 밖으로 나갑니다." % pl["line"])
            elif bd[0] < cb[0] or bd[1] < cb[1] or bd[2] > cb[2] or bd[3] > cb[3]:
                errors.append("대사 '%s' 풍선(꼬리 포함)이 내보내기 크롭 영역 밖으로 나가 잘립니다." % pl["line"])
            rects.append((pl["line"], pl["box"]))
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                if _overlap(rects[i][1], rects[j][1]):
                    warns.append("풍선 '%s' 와 '%s' 가 겹칩니다." % (rects[i][0], rects[j][0]))
    # lettered.png 최신 여부
    errors += proj.stale_problems(ep, n)
    if not pj.get("approved"):
        warns.append("아직 승인되지 않았습니다.")
    attrs = []
    for cid in page.get("cast") or []:
        try:
            attrs += proj.load_char(cid).get("check_attributes") or []
        except Exception:
            pass
    allow = page.get("in_image_text") or []
    visual = [t.format(attrs=", ".join(attrs) or "(check_attributes 없음)",
                       allow=(" — 허용: " + ", ".join(allow)) if allow else " — 허용 글자 없음")
              for t in VISUAL_ITEMS]
    return {"page": n, "errors": errors, "warnings": warns, "approved": bool(pj.get("approved")), "visual_checks": visual}


def run(proj, ep):
    sb, _ = proj.valid_storyboard(ep)
    res = [check_page(proj, ep, p) for p in sorted(sb["pages"], key=lambda p: p["n"])]
    out = {"episode": ep, "pages": res,
           "errors": sum(len(r["errors"]) for r in res), "warnings": sum(len(r["warnings"]) for r in res)}
    write_json(os.path.join(proj.ep_dir(ep), "qa.json"), out)
    return out


def summary(out):
    lines = []
    for r in out["pages"]:
        mark = "FAIL" if r["errors"] else ("warn" if r["warnings"] else "ok")
        lines.append("[%s] %d장%s" % (mark, r["page"], " (승인)" if r["approved"] else ""))
        for e in r["errors"]:
            lines.append("    오류: " + e)
        for w in r["warnings"]:
            lines.append("    경고: " + w)
    lines.append("")
    lines.append("자동 검사: 오류 %d, 경고 %d" % (out["errors"], out["warnings"]))
    lines.append("자동 검사가 잡지 못하는 것 — 아래는 lettered.png 를 직접 보고 확인해야 합니다:")
    for r in out["pages"]:
        lines.append("  %d장" % r["page"])
        for t in r["visual_checks"]:
            lines.append("    [ ] " + t)
    return "\n".join(lines)

