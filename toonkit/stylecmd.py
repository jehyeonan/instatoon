"""toon style ... 명령 (0단계, 정지점 G0)."""
import glob
import json
import os
import re
import shutil

from PIL import Image

from . import prompts
from .styles import DEFAULT_ACCENT, PALETTES, PRESETS, get_preset
from .util import RATIO_MAX, RATIO_MIN, ToonError, now, verify_image

DEFAULT_SCENE = ("a generic young office worker at a desk with a laptop and a coffee mug, upper body, "
                 "simple office background, one speech-bubble-free empty area on the top")
REF_SENTENCE = ("Match the drawing style of the attached reference image(s): line quality, shading, color palette, "
                "proportions. Do not copy their characters, faces, logos or text. The person in this scene must look "
                "clearly different from anyone in the reference: a different hairstyle, face shape, outfit and "
                "accessories (for example no lanyard or glasses if the reference has them).")


def out(msg=""):
    print(msg)


def style_dir(proj):
    return os.path.join(proj.root, "style")


def ensure_style(series):
    st = series.get("style")
    if not isinstance(st, dict):
        st = {}
    series["style"] = st
    st.setdefault("preset", None)
    st.setdefault("bible", "")
    st.setdefault("palette", "bw")
    st.setdefault("references", [])
    st.setdefault("samples", [])
    st.setdefault("approved_sample", None)
    return st


def apply_style(proj, preset=None, bible=None, palette=None):
    """style 값을 바꾼다. 바뀌었고 승인 샘플이 있으면 승인을 해제한다. 해제했는지 돌려준다."""
    st = ensure_style(proj.series)
    old = (st["preset"], st["bible"], st["palette"])
    if preset:
        p = get_preset(preset)
        if not p:
            raise ToonError("없는 프리셋입니다: %s (toon style presets 로 목록 확인)" % preset)
        st["preset"], st["bible"] = p["id"], p["bible"]
        st["palette"] = palette or p["palette"]
        cover = proj.series.get("cover")
        if isinstance(cover, dict) and str(cover.get("accent_color", DEFAULT_ACCENT)).upper() == DEFAULT_ACCENT:
            cover["accent_color"] = p["accent"]
    else:
        if bible is not None:
            if not bible.strip():
                raise ToonError("--bible 이 비어 있습니다.")
            st["preset"], st["bible"] = None, bible.strip()
        if palette:
            st["palette"] = palette
    released = False
    if (st["preset"], st["bible"], st["palette"]) != old and st.get("approved_sample"):
        st["approved_sample"] = None
        released = True
    proj.save_series()
    return released


def _sample(st, version):
    for s in st["samples"]:
        if s.get("version") == version:
            return s
    return None


def _refs_abs(proj):
    return [os.path.abspath(proj.resolve(r)) for r in ensure_style(proj.series)["references"]]


def cmd_presets(proj, a):
    out("id | 이름 | 설명 | 어울리는 소재/독자")
    for p in PRESETS:
        out("%s | %s | %s | %s" % (p["id"], p["name"], p["summary"], p["audience"]))


def cmd_set(proj, a):
    if not a.preset and a.bible is None and not a.palette:
        raise ToonError("--preset 또는 --bible 중 하나가 필요합니다.")
    if a.preset and a.bible is not None:
        raise ToonError("--preset 과 --bible 은 함께 쓸 수 없습니다.")
    released = apply_style(proj, a.preset, a.bible, a.palette)
    st = proj.series["style"]
    if a.preset:
        p = get_preset(a.preset)
        out("프리셋 %s(%s) 적용. palette=%s, 권장 대사 폰트 역할=%s" % (p["id"], p["name"], st["palette"], p["font"]))
    else:
        out("그림체를 직접 작성한 bible 로 바꿨습니다. palette=%s" % st["palette"])
    if released:
        out("경고: 그림체가 바뀌어 승인된 샘플의 승인을 해제했습니다. toon style prompt 로 샘플을 다시 만들고 다시 승인하세요.")


def cmd_ref(proj, a):
    st = ensure_style(proj.series)
    if a.rc == "list":
        if not st["references"]:
            out("레퍼런스 이미지가 없습니다.")
        for r in st["references"]:
            out(r)
        return
    for src in a.images:
        if not os.path.isfile(src):
            raise ToonError("파일이 없습니다: %s" % src)
        verify_image(src)
    d = os.path.join(style_dir(proj), "refs")
    os.makedirs(d, exist_ok=True)
    nums = [int(m.group(1)) for r in st["references"] for m in [re.search(r"ref_(\d+)\.", os.path.basename(r))] if m]
    nums += [int(m.group(1)) for f in glob.glob(os.path.join(d, "ref_*")) for m in [re.search(r"ref_(\d+)\.", os.path.basename(f))] if m]
    n = max(nums or [0])
    for src in a.images:
        n += 1
        ext = os.path.splitext(src)[1].lower() or ".png"
        dest = os.path.join(d, "ref_%02d%s" % (n, ext))
        shutil.copyfile(src, dest)
        st["references"].append(proj.store_path(dest))
        out("레퍼런스 추가: %s" % proj.store_path(dest))
    proj.save_series()
    out("view_image 로 레퍼런스를 보고 선·명암·색·등신·배경 밀도를 영문 bible 로 적어 toon style set --bible 로 저장하세요.")


def sample_prompt(proj, bible, scene, with_refs):
    s = proj.series
    parts = [prompts.FORMAT, "STYLE: " + bible.strip()]
    if with_refs:
        parts.append(REF_SENTENCE)
    parts.append("SCENE: " + scene.strip())
    parts.append(prompts.NO_TEXT)
    if s.get("negative"):
        parts.append("AVOID: " + s["negative"].strip())
    parts.append(prompts.FORMAT)
    return "\n\n".join(parts) + "\n"


def cmd_prompt(proj, a):
    st = ensure_style(proj.series)
    targets = []
    if a.presets:
        for pid in [x.strip() for x in a.presets.split(",") if x.strip()]:
            p = get_preset(pid)
            if not p:
                raise ToonError("없는 프리셋입니다: %s" % pid)
            targets.append((p["id"], p["bible"]))
        if not targets:
            raise ToonError("--presets 가 비어 있습니다.")
    else:
        bible = proj.style_bible()
        if not st["bible"].strip() and not bible:
            raise ToonError("그림체가 비어 있습니다. toon style set --preset/--bible 로 먼저 정하세요.")
        targets.append((st.get("preset"), bible))
    scene = a.scene or DEFAULT_SCENE
    refs = _refs_abs(proj)
    d = style_dir(proj)
    os.makedirs(d, exist_ok=True)
    have = [int(m.group(1)) for f in glob.glob(os.path.join(d, "sample_prompt_v*.txt"))
            for m in [re.search(r"sample_prompt_v(\d+)", os.path.basename(f))] if m]
    n = max(have or [0]) + 1
    jobs = []
    for pid, bible in targets:
        name = "sample_prompt_v%d%s.txt" % (n, "_" + pid if pid else "")
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(sample_prompt(proj, bible, scene, bool(refs)))
        jobs.append({"preset": pid, "prompt_file": os.path.abspath(path), "referenced_image_paths": list(refs)})
    out(json.dumps(jobs, ensure_ascii=False, indent=2))


def cmd_ingest(proj, a):
    st = ensure_style(proj.series)
    if not os.path.isfile(a.png):
        raise ToonError("파일이 없습니다: %s" % a.png)
    if a.preset and not get_preset(a.preset):
        raise ToonError("없는 프리셋입니다: %s" % a.preset)
    verify_image(a.png)
    v = max([s["version"] for s in st["samples"]] or [0]) + 1
    os.makedirs(style_dir(proj), exist_ok=True)
    dest = os.path.join(style_dir(proj), "sample_v%d.png" % v)
    with Image.open(a.png) as im:
        w, h = im.size
        im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").save(dest, "PNG")
    r = w / float(h)
    ent = {"version": v, "file": proj.store_path(dest), "preset": a.preset, "rejected": False, "size": [w, h], "ts": now()}
    if not (RATIO_MIN <= r <= RATIO_MAX):
        ent["rejected"] = True
        ent["reason"] = "비율 %.3f (%dx%d): 세로 4:5(%.2f~%.2f)가 아님" % (r, w, h, RATIO_MIN, RATIO_MAX)
    st["samples"].append(ent)
    proj.save_series()
    if ent["rejected"]:
        out("경고: 샘플 v%d 는 rejected 로 기록했습니다(파일은 보관). %s — 다시 생성하세요." % (v, ent["reason"]))
    else:
        out("샘플 v%d 등록: %s (승인하려면 toon style approve --version %d)" % (v, ent["file"], v))


def cmd_approve(proj, a):
    st = ensure_style(proj.series)
    if a.version:
        s = _sample(st, a.version)
        if not s:
            raise ToonError("샘플 v%s 가 없습니다." % a.version)
    else:
        ok = [x for x in st["samples"] if not x.get("rejected")]
        if not ok:
            raise ToonError("승인할 수 있는 샘플이 없습니다(toon style ingest 먼저).")
        s = ok[-1]
    if s.get("rejected"):
        raise ToonError("샘플 v%s 는 rejected 라 승인할 수 없습니다." % s["version"])
    if not os.path.isfile(proj.resolve(s["file"])):
        raise ToonError("샘플 파일이 없습니다: %s" % s["file"])
    if s.get("preset") and s["preset"] != st.get("preset"):
        apply_style(proj, preset=s["preset"])
        out("샘플의 프리셋 %s 에 맞춰 bible/palette 를 바꿨습니다." % s["preset"])
        st = proj.series["style"]
    st["approved_sample"] = s["file"]
    proj.save_series()
    out("승인된 그림체 샘플: %s. 캐릭터 시트를 만들 때 이 이미지가 참조 맨 앞에 들어갑니다." % s["file"])


def status_line(proj):
    st = proj.series.get("style") or {}
    if st.get("preset"):
        kind = "프리셋 %s" % st["preset"]
    elif (st.get("bible") or "").strip():
        kind = "직접 작성"
    elif proj.style_bible() and proj.style_bible() != "":
        kind = "구버전 style_bible"
    else:
        kind = "미설정"
    ok = [s for s in st.get("samples", []) if not s.get("rejected")]
    return "그림체: %s, 레퍼런스 %d장, 샘플 %d장(거부 %d), 승인 %s" % (
        kind, len(st.get("references", [])), len(ok), len(st.get("samples", [])) - len(ok),
        st.get("approved_sample") or "안 됨")


def run(proj, a):
    {"presets": cmd_presets, "set": cmd_set, "ref": cmd_ref, "prompt": cmd_prompt,
     "ingest": cmd_ingest, "approve": cmd_approve}[a.sc](proj, a)

