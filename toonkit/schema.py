import re

PAGE_KINDS = ("cover", "body", "ending")
LINE_KINDS = ("speech", "thought", "narration", "shout", "sfx")
MAX_LINE_CHARS = 40
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _is_box(b):
    return (isinstance(b, (list, tuple)) and len(b) == 4
            and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in b))


def check_series(s):
    errors = []
    if not isinstance(s.get("title"), str) or not s["title"].strip():
        errors.append("series.json: title 이 비어 있습니다.")
    c = s.get("canvas")
    if c is not None:
        if not (isinstance(c, list) and len(c) == 2 and all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in c)):
            errors.append("series.json: canvas 는 [너비, 높이] 정수여야 합니다.")
        elif c[0] * 5 != c[1] * 4:
            errors.append("series.json: canvas 는 4:5 세로만 지원합니다(예: [1080, 1350]). 지금 값: %s" % c)
    for fld in ("accent_color", "text_color", "stroke_color"):
        v = (s.get("cover") or {}).get(fld)
        if v is not None and not (isinstance(v, str) and COLOR_RE.match(v)):
            errors.append("series.json: cover.%s 는 #RGB 또는 #RRGGBB 형식이어야 합니다." % fld)
    for key, fld in (("cover", "title_area"), ("ending", "area")):
        area = (s.get(key) or {}).get(fld)
        if area is not None and not (_is_box(area) and all(0 <= x <= 1 for x in area) and area[0] < area[2] and area[1] < area[3]):
            errors.append("series.json: %s.%s 는 0~1 비율 [x0,y0,x1,y1] 이어야 합니다." % (key, fld))
    return errors


def check_storyboard(sb, char_ids):
    """(errors, warnings)"""
    errors, warns = [], []
    pages = sb.get("pages") if isinstance(sb, dict) else None
    if not isinstance(pages, list) or not pages:
        return ["storyboard.json: pages 가 비어 있습니다."], warns
    if len(pages) < 5 or len(pages) > 10:
        warns.append("장 수가 %d장입니다(권장 6~10장)." % len(pages))
    seen = set()
    for i, p in enumerate(pages):
        tag = "%d번째 항목" % (i + 1)
        if not isinstance(p, dict):
            errors.append("%s: 객체가 아닙니다." % tag)
            continue
        n = p.get("n")
        if not isinstance(n, int) or n < 1:
            errors.append("%s: n 은 1 이상 정수여야 합니다." % tag)
            continue
        tag = "%d장" % n
        if n in seen:
            errors.append("%s: 장 번호가 중복됩니다." % tag)
        seen.add(n)
        if p.get("kind") not in PAGE_KINDS:
            errors.append("%s: kind 는 cover|body|ending 중 하나여야 합니다." % tag)
        if not str(p.get("scene", "")).strip():
            errors.append("%s: scene 이 비어 있습니다." % tag)
        for cid in p.get("cast") or []:
            if not isinstance(cid, str) or not ID_RE.match(cid):
                errors.append("%s: 등장 캐릭터 id '%s' 는 영문, 숫자, _, - 만 쓸 수 있습니다." % (tag, cid))
            elif cid not in char_ids:
                errors.append("%s: 등장 캐릭터 '%s' 가 characters/ 에 없습니다." % (tag, cid))
        if not p.get("cast"):
            warns.append("%s: cast 가 비어 있어 캐릭터 시트가 첨부되지 않습니다." % tag)
        ids = set()
        for ln in p.get("lines") or []:
            lid = ln.get("id") if isinstance(ln, dict) else None
            if not lid:
                errors.append("%s: 대사에 id 가 없습니다." % tag)
                continue
            if lid in ids:
                errors.append("%s: 대사 id '%s' 중복." % (tag, lid))
            ids.add(lid)
            if ln.get("kind") not in LINE_KINDS:
                errors.append("%s/%s: kind 는 %s 중 하나." % (tag, lid, "|".join(LINE_KINDS)))
            text = str(ln.get("text", ""))
            if not text.strip():
                errors.append("%s/%s: text 가 비어 있습니다." % (tag, lid))
            elif len(text) > MAX_LINE_CHARS:
                warns.append("%s/%s: 대사가 %d자입니다(풍선당 %d자 초과, 나누는 편이 좋습니다)." % (tag, lid, len(text), MAX_LINE_CHARS))
        iit = p.get("in_image_text")
        if iit is not None and not (isinstance(iit, list) and all(isinstance(x, str) for x in iit)):
            errors.append("%s: in_image_text 는 문자열 목록이어야 합니다." % tag)
        ct = p.get("cover_title")
        if p.get("kind") == "cover":
            if ct is None:
                warns.append("%s: cover_title 이 없어 series.cover.title_lines 를 씁니다." % tag)
            elif not (isinstance(ct, list) and len(ct) == 3 and all(isinstance(x, str) and x.strip() for x in ct)):
                errors.append("%s: cover_title 은 3줄 문자열이어야 합니다." % tag)
    return errors, warns


def check_letter(letter):
    errors = []
    bl = letter.get("balloons") if isinstance(letter, dict) else None
    if not isinstance(bl, list):
        return ["letter.json: balloons 목록이 없습니다."]
    for i, b in enumerate(bl):
        tag = "balloons[%d]" % i
        if not isinstance(b, dict) or not b.get("line"):
            errors.append("%s: line(대사 id)이 없습니다." % tag)
            continue
        if b.get("kind") is not None and b["kind"] not in LINE_KINDS:
            errors.append("%s: kind 가 올바르지 않습니다." % tag)
        if not _is_box(b.get("box")):
            errors.append("%s: box 는 [x0,y0,x1,y1] 숫자 4개여야 합니다." % tag)
        elif not (b["box"][0] < b["box"][2] and b["box"][1] < b["box"][3]):
            errors.append("%s: box 의 x0<x1, y0<y1 이어야 합니다." % tag)
        if b.get("text") is not None and not isinstance(b["text"], str):
            errors.append("%s: text 는 문자열이어야 합니다." % tag)
        t = b.get("tail")
        if t is not None and not (isinstance(t, (list, tuple)) and len(t) == 2 and all(isinstance(x, (int, float)) for x in t)):
            errors.append("%s: tail 은 [x,y] 여야 합니다." % tag)
    return errors

