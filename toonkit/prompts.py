"""image_gen 에 그대로 넘길 프롬프트 파일 생성."""
import glob
import os
import re

from .util import ToonError

NO_TEXT = ("ABSOLUTELY NO text, NO letters, NO speech bubbles, NO caption boxes, NO logos anywhere in the image. "
           "Leave clean empty white space where speech bubbles will be added later.")

FORMAT = ("FORMAT: a single vertical 4:5 portrait comic page image (aspect ratio 4 wide : 5 tall, like 1080x1350). "
          "Never landscape, never square.")

SHEET_MAIN = ("Character design reference sheet on a plain white background: four-view turnaround "
              "(front, three-quarter, side, back) in a row, plus a row of 8 distinct facial expressions "
              "(neutral, happy, surprised, embarrassed, angry, sad, tired, smug) and a row of 3-4 signature props. "
              "Same character in every view, consistent proportions. No text, no labels, no logos.")
SHEET_SUPPORT = ("Compact character reference sheet on a plain white background: face in three views "
                 "(front, three-quarter, side) plus 4 facial expressions (neutral, happy, surprised, annoyed). "
                 "Same character in every view. No text, no labels, no logos.")


def next_version(directory, prefix, ext):
    best = 0
    for p in glob.glob(os.path.join(directory, "%s_v*.%s" % (prefix, ext))):
        m = re.search(r"_v(\d+)\.", os.path.basename(p))
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


def latest_version_file(directory, prefix, ext):
    n = next_version(directory, prefix, ext) - 1
    if n < 1:
        return None
    return os.path.join(directory, "%s_v%d.%s" % (prefix, n, ext))


def write_versioned(directory, prefix, ext, text):
    """직전 버전과 내용이 같으면 재사용, 다르면 새 버전. (경로, 새로 만들었는지)"""
    os.makedirs(directory, exist_ok=True)
    last = latest_version_file(directory, prefix, ext)
    if last:
        with open(last, encoding="utf-8") as f:
            if f.read() == text:
                return last, False
    n = next_version(directory, prefix, ext)
    path = os.path.join(directory, "%s_v%d.%s" % (prefix, n, ext))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, True


STYLE_SAMPLE_SENTENCE = ("Match the drawing style of the first attached image (style sample); "
                         "draw a new character, do not copy that image's person.")


def sheet_refs(proj):
    """캐릭터 시트 생성에 넘길 참조 이미지(승인된 그림체 샘플이 맨 앞)."""
    s = proj.approved_sample()
    return [s] if s else []


def sheet_prompt(proj, cid):
    c = proj.load_char(cid)
    parts = [proj.style_bible()]
    if proj.series.get("negative"):
        parts.append("Avoid: " + proj.series["negative"].strip())
    if sheet_refs(proj):
        parts.append(STYLE_SAMPLE_SENTENCE)
    parts.append("CHARACTER: " + (c.get("lock_prompt") or "(lock_prompt 를 character.json 에 먼저 채우세요)").strip())
    parts.append(SHEET_MAIN if c.get("role", "main") == "main" else SHEET_SUPPORT)
    return "\n\n".join(p for p in parts if p) + "\n"


def page_prompt(proj, page, with_sheets=True):
    kind = page.get("kind")
    s = proj.series
    parts = [FORMAT]
    if proj.style_bible():
        parts.append("STYLE: " + proj.style_bible())
    if s.get("negative"):
        parts.append("AVOID: " + s["negative"].strip())
    cast = page.get("cast") or []
    if cast:
        block = []
        for cid in cast:
            c = proj.load_char(cid)
            block.append("- %s: %s" % (c.get("name", cid), (c.get("lock_prompt") or "").strip()))
        head = "CHARACTERS (the attached reference sheet shows each one; keep them identical, do not copy the sheet layout):" if with_sheets else "CHARACTERS:"
        parts.append(head + "\n" + "\n".join(block))
    scene = str(page.get("scene", "")).strip()
    if scene.upper().startswith("TODO"):
        raise ToonError("%d장: scene 이 아직 TODO 입니다." % page["n"])
    parts.append("SCENE: " + scene)
    if page.get("panels"):
        parts.append("PANELS: " + str(page["panels"]).strip())
    if kind == "cover":
        parts.append("LAYOUT: keep the top 40% of the image as clean empty white space (the title is added later); "
                     "place the character and the main subject in the bottom 60%.")
    elif kind == "ending":
        parts.append("LAYOUT: keep the bottom 35% of the image as clean empty white space (ending text is added later).")
    parts.append(NO_TEXT)
    allow = page.get("in_image_text") or []
    if allow:
        parts.append("The ONLY text allowed anywhere in the image, spelled exactly as written: "
                     + ", ".join('"%s"' % t for t in allow)
                     + ". Every other surface must have no letters.")
    parts.append(FORMAT)
    return "\n\n".join(parts) + "\n"

