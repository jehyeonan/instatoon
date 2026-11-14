"""toon 명령줄. python -m toonkit.cli <명령>"""
import argparse
import contextlib
import fcntl
import json
import os
import shutil
import sys

from PIL import Image

from . import exporter, lettering, prompts, qa as qa_mod, schema, stylecmd
from .styles import PALETTES, TEMPLATE_BIBLE
from .project import Project
from .util import RATIO_MAX, RATIO_MIN, ToonError, find_root, norm_ep, norm_page, now, read_json, verify_image, write_json


def out(msg=""):
    print(msg)


def pages_arg(s, sb):
    allp = sorted(p["n"] for p in sb["pages"])
    if not s:
        return allp
    want = [norm_page(x) for x in s.split(",") if x.strip()]
    for n in want:
        if n not in allp:
            raise ToonError("storyboard 에 %d장이 없습니다." % n)
    return want


# ---------- init / character / episode ----------

SERIES_TEMPLATE = {
    "title": "",
    "style": {"preset": None, "bible": "", "palette": "bw", "references": [], "samples": [], "approved_sample": None},
    "style_bible": TEMPLATE_BIBLE,
    "negative": "브랜드 로고, 상표, 워터마크, 실존 인물 얼굴",
    "cover": {
        "title_lines": ["첫째 줄", "강조할 가운데 줄", "셋째 줄"],
        "accent_line": 2,
        "accent_color": "#E02020",
        "text_color": "#111111",
        "stroke_color": "#111111",
        "title_area": [0.05, 0.03, 0.95, 0.38],
        "label_template": "시리즈 이름 EP.{n}",
    },
    "ending": {
        "series_line": "시리즈 이름",
        "tagline": "다음 화에 또 만나요",
        "follow_text": "취향에 맞으면 팔로우",
        "area": [0.08, 0.68, 0.92, 0.96],
    },
    "canvas": [1080, 1350],
}


def cmd_init(a):
    d = os.path.abspath(a.dir)
    if os.path.exists(os.path.join(d, "series.json")):
        raise ToonError("이미 series.json 이 있습니다: %s" % d)
    os.makedirs(d, exist_ok=True)
    s = dict(SERIES_TEMPLATE)
    s["style"] = json.loads(json.dumps(SERIES_TEMPLATE["style"]))
    s["title"] = a.title
    if a.handle:
        s["handle"] = a.handle
    s["cover"] = dict(SERIES_TEMPLATE["cover"], label_template="%s EP.{n}" % a.title)
    s["ending"] = dict(SERIES_TEMPLATE["ending"], series_line=a.title)
    write_json(os.path.join(d, "series.json"), s)
    for sub in ("characters", "episodes", "style"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    out("시리즈 폴더를 만들었습니다: %s" % d)
    out("다음: toon style presets 로 그림체부터 정하세요(레퍼런스가 있으면 toon style ref add). 그다음 toon character add <id> --name ... --role main")


def require_style(proj, no_style):
    """승인된 그림체 샘플이 없으면 거부한다. 옛 시리즈(style 없음 + 직접 쓴 style_bible + 승인 시트 있음)는 경고만."""
    if no_style or proj.approved_sample():
        return
    legacy = (not proj.series.get("style") and proj.style_bible() not in ("", TEMPLATE_BIBLE)
              and any(proj.approved_sheet(c) for c in proj.char_ids()))
    if legacy:
        out("경고: 승인된 그림체 샘플이 없습니다(옛 시리즈라 계속 진행). toon style 로 그림체 샘플을 승인해 두는 편이 좋습니다.")
        return
    raise ToonError("승인된 그림체 샘플이 없습니다. toon style ... 로 그림체부터 정하세요(toon style presets, toon style prompt, "
                    "toon style ingest, toon style approve). 건너뛰려면 --no-style.")


def sheet_job(proj, path):
    refs = prompts.sheet_refs(proj)
    out("image_gen 참조 이미지(referenced_image_paths): %s" % json.dumps([os.path.abspath(r) for r in refs], ensure_ascii=False))
    out("image_gen 프롬프트 파일: %s" % os.path.abspath(path))


def cmd_style(a):
    proj = Project.open(a.root)
    stylecmd.run(proj, a)


def cmd_character(a):
    proj = Project.open(a.root)
    if a.cc == "add":
        cd = proj.char_dir(a.id)
        if os.path.exists(os.path.join(cd, "character.json")):
            raise ToonError("이미 있는 캐릭터입니다: %s" % a.id)
        require_style(proj, a.no_style)
        os.makedirs(cd, exist_ok=True)
        proj.save_char(a.id, {"name": a.name or a.id, "role": a.role, "lock_prompt": "",
                              "check_attributes": [], "sheets": [], "approved_sheet": None})
        p, _ = prompts.write_versioned(cd, "sheet_prompt", "txt", prompts.sheet_prompt(proj, a.id))
        out("캐릭터 폴더: %s" % cd)
        out("lock_prompt 와 check_attributes 를 character.json 에 채운 뒤 'toon character prompt %s' 로 시트 프롬프트를 다시 만드세요." % a.id)
        out("시트 프롬프트 파일: %s" % p)
        sheet_job(proj, p)
    elif a.cc == "prompt":
        proj.load_char(a.id)
        require_style(proj, a.no_style)
        p, new = prompts.write_versioned(proj.char_dir(a.id), "sheet_prompt", "txt", prompts.sheet_prompt(proj, a.id))
        out("%s %s" % ("새 파일" if new else "변경 없음(기존 파일)", p))
        sheet_job(proj, p)
    elif a.cc == "ingest":
        c = proj.load_char(a.id)
        if not os.path.isfile(a.png):
            raise ToonError("파일이 없습니다: %s" % a.png)
        verify_image(a.png)
        v = max([s["version"] for s in c.get("sheets", [])] or [0]) + 1
        name = "sheet_v%d.png" % v
        shutil.copyfile(a.png, os.path.join(proj.char_dir(a.id), name))
        c.setdefault("sheets", []).append({"version": v, "file": name, "source": proj.store_path(a.png), "ts": now()})
        proj.save_char(a.id, c)
        proj.log(ep=None, page=None, version=v, kind="sheet", character=a.id, ok=True)
        out("시트 v%d 등록: %s (승인하려면 toon character approve %s)" % (v, name, a.id))
    elif a.cc == "approve":
        c = proj.load_char(a.id)
        if not c.get("sheets"):
            raise ToonError("등록된 시트가 없습니다.")
        v = a.version or max(s["version"] for s in c["sheets"])
        f = [s["file"] for s in c["sheets"] if s["version"] == v]
        if not f:
            raise ToonError("시트 v%s 가 없습니다." % v)
        c["approved_sheet"] = f[0]
        proj.save_char(a.id, c)
        out("%s 의 승인 시트: %s" % (a.id, f[0]))


def cmd_episode(a):
    proj = Project.open(a.root)
    base = os.path.join(proj.root, "episodes")
    os.makedirs(base, exist_ok=True)
    if a.n:
        n = a.n
    else:
        have = [int(d[2:]) for d in os.listdir(base) if d.startswith("ep") and d[2:].isdigit()]
        n = max(have or [0]) + 1
    d = proj.ep_dir(n)
    if os.path.exists(d):
        raise ToonError("이미 있는 에피소드입니다: ep%02d" % n)
    os.makedirs(d)
    write_json(os.path.join(d, "episode.json"), {
        "number": n, "format": a.format, "topic_candidates": [], "chosen": "", "reason": "",
        "caption": "", "hashtags": [], "status": "draft"})
    pages = [{"n": 1, "kind": "cover", "scene": "TODO", "cast": [], "lines": [], "in_image_text": [],
              "cover_title": ["TODO", "TODO", "TODO"]}]
    for i in range(2, 8):
        pages.append({"n": i, "kind": "body", "scene": "TODO", "cast": [], "lines": [], "in_image_text": []})
    pages.append({"n": 8, "kind": "ending", "scene": "TODO", "cast": [], "lines": [], "in_image_text": []})
    write_json(os.path.join(d, "storyboard.json"), {"pages": pages})
    out("에피소드 폴더: %s" % d)


# ---------- prompt / ingest ----------

def validate_storyboard(proj, ep):
    sb, warns = proj.valid_storyboard(ep)
    for w in warns:
        out("경고: " + w)
    return sb


def cmd_prompt(a):
    proj = Project.open(a.root)
    ep = norm_ep(a.ep)
    sb = validate_storyboard(proj, ep)
    jobs = []
    stored = {}
    jp = os.path.join(proj.ep_dir(ep), "jobs.json")
    if os.path.isfile(jp):
        old = read_json(jp)
        if isinstance(old, list):
            stored = dict((j["page"], j) for j in old if isinstance(j, dict) and "page" in j)
    for n in pages_arg(a.pages, sb):
        page = lettering.sb_page(sb, n)
        refs = []
        for cid in page.get("cast") or []:
            sheet = proj.approved_sheet(cid)
            if not sheet:
                if a.no_sheets:
                    continue
                raise ToonError("캐릭터 '%s' 의 승인된 시트가 없습니다(toon character ingest/approve). 시트 없이 가려면 --no-sheets." % cid)
            refs.append(sheet)
        text = prompts.page_prompt(proj, page, with_sheets=bool(refs))
        path, new = prompts.write_versioned(proj.page_dir(ep, n), "prompt", "txt", text)
        stored[n] = {"page": n, "prompt_file": proj.store_path(path),
                     "referenced_image_paths": [proj.store_path(r) for r in refs]}
        jobs.append({"page": n, "prompt_file": os.path.abspath(path),
                     "referenced_image_paths": [os.path.abspath(r) for r in refs]})
    write_json(jp, [stored[k] for k in sorted(stored)])
    out(json.dumps(jobs, ensure_ascii=False, indent=2))


def cmd_ingest(a):
    proj = Project.open(a.root)
    ep, n = norm_ep(a.ep), norm_page(a.page)
    sb = proj.load_storyboard(ep)
    lettering.sb_page(sb, n)
    if not os.path.isfile(a.png):
        raise ToonError("파일이 없습니다: %s" % a.png)
    verify_image(a.png)
    pj = proj.page_json(ep, n)
    v = max([x["v"] for x in pj["versions"]] or [0]) + 1
    kind = "edit" if a.edit_of else "new"
    pd = proj.page_dir(ep, n)
    os.makedirs(pd, exist_ok=True)
    name = "gen_v%d.png" % v
    dest = os.path.join(pd, name)
    shutil.copyfile(a.png, dest)
    with Image.open(dest) as im:
        w, h = im.size
    r = w / float(h)
    reason = None
    if not (RATIO_MIN <= r <= RATIO_MAX):
        reason = "비율 %.3f (%dx%d): 세로 4:5(%.2f~%.2f)가 아님" % (r, w, h, RATIO_MIN, RATIO_MAX)
    refs, pf = [], None
    jp = os.path.join(proj.ep_dir(ep), "jobs.json")
    if os.path.isfile(jp):
        for j in read_json(jp):
            if j.get("page") == n:
                refs = [proj.store_path(x) for x in j.get("referenced_image_paths", [])]
                pf = proj.store_path(j["prompt_file"]) if j.get("prompt_file") else None
    ent = {"v": v, "file": name, "source": proj.store_path(a.png), "refs": refs, "prompt_file": pf,
           "ts": now(), "kind": kind, "base": a.edit_of, "size": [w, h]}
    if reason:
        ent["rejected"] = True
        ent["reason"] = reason
    pj["versions"].append(ent)
    if not reason:
        pj["chosen"] = v
        pj["approved"] = False
        pj.pop("approved_at", None)
        pj["status"] = "generated"
    proj.save_page_json(ep, n, pj)
    proj.log(ep=ep, page=n, version=v, kind=kind, ok=not reason, reason=reason)
    if reason:
        out("경고: v%d 는 rejected 로 기록했습니다(파일은 보관). %s — 폐기하고 재생성하세요." % (v, reason))
    else:
        out("%d장 v%d 등록 (%dx%d). 채택 버전으로 지정했습니다." % (n, v, w, h))


# ---------- grid / letter / qa / approve / export / status ----------

def cmd_grid(a):
    proj = Project.open(a.root)
    out(lettering.draw_grid(proj, norm_ep(a.ep), norm_page(a.page)))


def cmd_letter(a):
    proj = Project.open(a.root)
    ep = norm_ep(a.ep)
    sb, _ = proj.valid_storyboard(ep)
    bad = 0
    for n in pages_arg(a.pages, sb):
        page = lettering.sb_page(sb, n)
        v, src = proj.chosen_file(ep, n)
        if not src:
            out("%d장: 이미지 없음 — 건너뜀. %s" % (n, proj.no_image_hint(ep, n)))
            continue
        proj.require_usable(ep, n)
        lp = os.path.join(proj.page_dir(ep, n), "letter.json")
        if page.get("lines") and not os.path.isfile(lp):
            out("경고: %d장에 대사가 있지만 letter.json 이 없습니다." % n)
        rep = lettering.render_page(proj, ep, n)
        flag = ""
        if rep["overflow"] or rep["issues"]:
            bad += 1
            flag = " 넘침=%s 문제=%s" % (rep["overflow"], rep["issues"])
        out("%d장: lettered.png (풍선 %d개)%s" % (n, rep["balloons"], flag))
        pj = proj.page_json(ep, n)
        if pj.get("approved"):
            out("%d장: 다시 식자해서 승인을 해제했습니다. 확인 후 toon approve 를 다시 실행하세요." % n)
        pj["approved"] = False
        pj.pop("approved_at", None)
        pj["status"] = "lettered"
        proj.save_page_json(ep, n, pj)
    if bad:
        sys.exit(1)


def cmd_qa(a):
    proj = Project.open(a.root)
    res = qa_mod.run(proj, norm_ep(a.ep))
    out(qa_mod.summary(res))
    if res["errors"]:
        sys.exit(1)


def _qa_errors(proj, ep, n):
    p = os.path.join(proj.ep_dir(ep), "qa.json")
    if not os.path.isfile(p):
        return []
    for r in read_json(p).get("pages") or []:
        if r.get("page") == n:
            return list(r.get("errors") or [])
    return []


def cmd_approve(a):
    proj = Project.open(a.root)
    ep, n = norm_ep(a.ep), norm_page(a.page)
    pj = proj.page_json(ep, n)
    if not pj["versions"]:
        raise ToonError("%d장에 등록된 버전이 없습니다." % n)
    if a.version:
        ent = [x for x in pj["versions"] if x["v"] == a.version]
        if not ent:
            raise ToonError("v%s 가 없습니다." % a.version)
        if ent[0].get("rejected"):
            raise ToonError("v%s 는 rejected 라 승인할 수 없습니다." % a.version)
        pj["chosen"] = a.version  # 검사를 모두 통과한 뒤에만 저장한다
    v, _ = proj.require_usable(ep, n, pj)
    problems = proj.stale_problems(ep, n, pj)
    if problems:
        raise ToonError("승인할 수 없습니다:\n  " + "\n  ".join(problems))
    if not a.force:
        errs = _qa_errors(proj, ep, n)
        if errs:
            raise ToonError("승인할 수 없습니다. 마지막 qa 결과에 %d장 오류가 있습니다(고친 뒤 toon qa 를 다시 실행하거나 --force):\n  " % n + "\n  ".join(errs))
    pj["chosen"] = v
    pj["approved"] = True
    pj["status"] = "approved"
    pj["approved_at"] = now()
    proj.save_page_json(ep, n, pj)
    out("%d장 v%s 승인" % (n, v))


def cmd_export(a):
    proj = Project.open(a.root)
    ep = norm_ep(a.ep)
    path, count = exporter.export(proj, ep, force=a.force)
    out("%d장 내보냄: %s" % (count, path))
    out("확인: %s/preview.jpg, caption.txt (게시는 직접 하세요)" % path)


def cmd_status(a):
    proj = Project.open(a.root)
    rows = proj.ledger()
    base = os.path.join(proj.root, "episodes")
    eps = [norm_ep(a.ep)] if a.ep else sorted(int(d[2:]) for d in os.listdir(base) if d.startswith("ep") and d[2:].isdigit()) if os.path.isdir(base) else []
    out("시리즈: %s" % proj.series.get("title"))
    out(stylecmd.status_line(proj))
    for c in proj.char_ids():
        out("캐릭터 %s: 승인 시트 %s" % (c, proj.load_char(c).get("approved_sheet") or "없음"))
    for ep in eps:
        try:
            sb = proj.load_storyboard(ep)
        except ToonError:
            continue
        gens = [r for r in rows if r.get("ep") == ep and r.get("kind") in ("new", "edit")]
        pages_with = len(set(r["page"] for r in gens))
        rate = (len(gens) - pages_with) / float(len(gens)) if gens else 0.0
        out("EP.%d: 생성 %d회, 재생성률 %.0f%%" % (ep, len(gens), rate * 100))
        for p in sorted(sb["pages"], key=lambda p: p["n"]):
            n = p["n"]
            pj = proj.page_json(ep, n)
            has_l = os.path.isfile(os.path.join(proj.page_dir(ep, n), "lettered.png"))
            out("  %d장 [%s] %s 버전 %d개, 채택 %s%s%s" % (n, p.get("kind"), pj.get("status"), len(pj["versions"]),
                "v%s" % pj["chosen"] if pj.get("chosen") else "-", ", 식자됨" if has_l else "", ", 승인" if pj.get("approved") else ""))
    allg = [r for r in rows if r.get("kind") in ("new", "edit")]
    out("전체 생성 %d회" % len(allg))


def build_parser():
    ap = argparse.ArgumentParser(prog="toon", description="연재 인스타툰 제작 도구")
    ap.add_argument("--root", default=None, help="시리즈 폴더(기본: 현재 위치에서 위로 series.json 탐색)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS)
    sp = ap.add_subparsers(dest="cmd")
    sp.required = True

    s = sp.add_parser("init", parents=[common]); s.add_argument("dir"); s.add_argument("--title", required=True); s.add_argument("--handle"); s.set_defaults(fn=cmd_init)
    c = sp.add_parser("character", parents=[common]); cs = c.add_subparsers(dest="cc"); cs.required = True
    x = cs.add_parser("add", parents=[common]); x.add_argument("id"); x.add_argument("--name"); x.add_argument("--role", choices=["main", "support"], default="main"); x.add_argument("--no-style", action="store_true")
    x = cs.add_parser("prompt", parents=[common]); x.add_argument("id"); x.add_argument("--no-style", action="store_true")
    x = cs.add_parser("ingest", parents=[common]); x.add_argument("id"); x.add_argument("png")
    x = cs.add_parser("approve", parents=[common]); x.add_argument("id"); x.add_argument("--version", type=int)
    c.set_defaults(fn=cmd_character)
    s = sp.add_parser("style", parents=[common]); ss = s.add_subparsers(dest="sc"); ss.required = True
    ss.add_parser("presets", parents=[common])
    x = ss.add_parser("set", parents=[common]); x.add_argument("--preset"); x.add_argument("--bible"); x.add_argument("--palette", choices=PALETTES)
    x = ss.add_parser("ref", parents=[common]); rs = x.add_subparsers(dest="rc"); rs.required = True
    y = rs.add_parser("add", parents=[common]); y.add_argument("images", nargs="+")
    rs.add_parser("list", parents=[common])
    x = ss.add_parser("prompt", parents=[common]); x.add_argument("--presets"); x.add_argument("--scene")
    x = ss.add_parser("ingest", parents=[common]); x.add_argument("png"); x.add_argument("--preset")
    x = ss.add_parser("approve", parents=[common]); x.add_argument("--version", type=int)
    s.set_defaults(fn=cmd_style)
    s = sp.add_parser("episode", parents=[common]); es = s.add_subparsers(dest="ec"); es.required = True
    x = es.add_parser("new", parents=[common]); x.add_argument("--n", type=int); x.add_argument("--format", default="ranking")
    s.set_defaults(fn=cmd_episode)
    s = sp.add_parser("prompt", parents=[common]); s.add_argument("ep"); s.add_argument("--pages"); s.add_argument("--no-sheets", action="store_true"); s.set_defaults(fn=cmd_prompt)
    s = sp.add_parser("ingest", parents=[common]); s.add_argument("ep"); s.add_argument("page"); s.add_argument("png"); s.add_argument("--edit-of", type=int); s.set_defaults(fn=cmd_ingest)
    s = sp.add_parser("grid", parents=[common]); s.add_argument("ep"); s.add_argument("page"); s.set_defaults(fn=cmd_grid)
    s = sp.add_parser("letter", parents=[common]); s.add_argument("ep"); s.add_argument("--pages"); s.set_defaults(fn=cmd_letter)
    s = sp.add_parser("qa", parents=[common]); s.add_argument("ep"); s.set_defaults(fn=cmd_qa)
    s = sp.add_parser("approve", parents=[common]); s.add_argument("ep"); s.add_argument("page"); s.add_argument("--version", type=int); s.add_argument("--force", action="store_true", help="마지막 qa 오류를 무시하고 승인"); s.set_defaults(fn=cmd_approve)
    s = sp.add_parser("export", parents=[common]); s.add_argument("ep"); s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_export)
    s = sp.add_parser("status", parents=[common]); s.add_argument("ep", nargs="?"); s.set_defaults(fn=cmd_status)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        with series_lock(a):
            a.fn(a)
    except ToonError as e:
        print("오류: %s" % e, file=sys.stderr)
        return 2
    return 0


@contextlib.contextmanager
def series_lock(a):
    """같은 시리즈에 대한 toon 명령을 한 번에 하나씩 실행한다.

    에이전트가 생성 결과를 병렬로 ingest 하면 같은 버전 번호를 받아 서로 덮어쓰므로,
    시리즈 루트의 .toon.lock 에 배타 잠금을 건다. 시리즈를 못 찾는 명령(init 등)은 잠그지 않는다.
    """
    try:
        root = find_root(getattr(a, "root", None), explicit=bool(getattr(a, "root", None)))
    except ToonError:
        yield
        return
    with open(os.path.join(root, ".toon.lock"), "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


if __name__ == "__main__":
    sys.exit(main())

