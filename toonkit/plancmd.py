"""toon plan ... 명령 (정지점 P)."""
import copy
import json
import os

from . import formats, planning
from .util import ToonError


def out(msg=""):
    print(msg)


def _csv(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def _blank(v):
    return v if v not in (None, "", []) else "(비어 있음)"


def cmd_show(proj, a):
    p = planning.ensure(copy.deepcopy(proj.series))
    out(planning.status_line(proj.series))
    pur = p["purpose"]
    out("목적: %s%s" % (_blank(pur), " — " + planning.PURPOSES[pur] if pur in planning.PURPOSES else ""))
    out("목적 메모: %s" % _blank(p["purpose_note"]))
    au = p["audience"]
    out("독자: %s / 고민: %s / 얻고 싶은 것: %s" % (_blank(au["who"]), _blank(au["pain"]), _blank(au["want"])))
    out("한 줄 소개: %s" % _blank(p["premise"]))
    out("콘텐츠 기둥:")
    for pl in p["pillars"] or []:
        out("  %s %s (%s%%) %s" % (pl.get("id"), pl.get("name"), pl.get("share", 0), pl.get("desc", "")))
    if not p["pillars"]:
        out("  (비어 있음)")
    out("말투: %s" % _blank(p["tone"]))
    out("연재 주기: %s" % _blank(p["cadence"]))
    out("포맷 조합: %s" % _blank(", ".join(p["format_mix"])))
    out("KPI: %s" % _blank(", ".join(p["kpi"])))
    out("수익 계획: %s" % _blank(", ".join(p["monetization"])))
    out("다루지 않을 것: %s" % _blank("; ".join(p["boundaries"])))
    out("참고: %s" % _blank("; ".join(p["references"])))
    if p.get("approved"):
        out("승인: %s" % p.get("approved_at"))


def _release_if_changed(proj, before):
    """승인 상태에서 내용이 바뀌면 승인 해제 + 경고."""
    plan = proj.series["plan"]
    if plan.get("approved") and planning.content(plan) != before:
        plan["approved"] = False
        plan["approved_at"] = None
        out("경고: 승인된 기획의 내용이 바뀌어 승인을 해제했습니다. toon plan check 후 toon plan approve 를 다시 하세요.")


def _load_file(path):
    if not os.path.isfile(path):
        raise ToonError("파일이 없습니다: %s" % path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        raise ToonError("plan 파일을 읽을 수 없습니다: %s" % e)
    if not isinstance(data, dict):
        raise ToonError("plan 파일은 JSON 객체여야 합니다.")
    return data


def cmd_set(proj, a):
    if a.purpose and a.purpose not in planning.PURPOSES:
        raise ToonError("purpose 는 %s 중 하나여야 합니다." % ", ".join(planning.PURPOSES))
    plan = planning.ensure(proj.series)
    before = copy.deepcopy(planning.content(plan))
    touched = False
    if a.file:
        for k, v in _load_file(a.file).items():
            if k in ("approved", "approved_at"):
                continue
            if k == "audience" and isinstance(v, dict):
                plan["audience"].update(v)
            else:
                plan[k] = v
        touched = True
    for k, v in (("purpose", a.purpose), ("premise", a.premise), ("tone", a.tone), ("cadence", a.cadence),
                 ("purpose_note", a.purpose_note)):
        if v is not None:
            plan[k] = v
            touched = True
    for k, v in (("kpi", a.kpi), ("monetization", a.monetization), ("format_mix", a.format_mix)):
        if v is not None:
            plan[k] = _csv(v)
            touched = True
    for k, v in (("who", a.who), ("pain", a.pain), ("want", a.want)):
        if v is not None:
            plan["audience"][k] = v
            touched = True
    if a.boundary:
        plan["boundaries"] = list(plan["boundaries"]) + [b for b in a.boundary if b not in plan["boundaries"]]
        touched = True
    if a.reference:
        plan["references"] = list(plan["references"]) + [r for r in a.reference if r not in plan["references"]]
        touched = True
    if not touched:
        raise ToonError("바꿀 값이 없습니다(--purpose, --premise, --tone, --cadence, --kpi, --monetization, --format-mix, "
                        "--who/--pain/--want, --boundary, --reference, --file).")
    _release_if_changed(proj, before)
    proj.save_series()
    out("기획을 저장했습니다. toon plan check 로 검증하세요.")


def cmd_pillar(proj, a):
    plan = planning.ensure(proj.series)
    before = copy.deepcopy(planning.content(plan))
    if a.pc == "add":
        nums = [int(x["id"][1:]) for x in plan["pillars"] if str(x.get("id", "")).startswith("p") and x["id"][1:].isdigit()]
        pid = "p%d" % (max(nums or [0]) + 1)
        plan["pillars"].append({"id": pid, "name": a.name, "desc": a.desc or "", "share": a.share})
        out("기둥 추가: %s %s (%s%%)" % (pid, a.name, a.share))
    else:
        keep = [x for x in plan["pillars"] if x.get("id") != a.id]
        if len(keep) == len(plan["pillars"]):
            raise ToonError("없는 기둥입니다: %s" % a.id)
        plan["pillars"] = keep
        out("기둥 삭제: %s" % a.id)
    _release_if_changed(proj, before)
    proj.save_series()
    out("기둥 %d개, share 합 %s" % (len(plan["pillars"]), sum(x.get("share", 0) for x in plan["pillars"])))


def cmd_check(proj, a):
    plan = planning.ensure(copy.deepcopy(proj.series))
    errs, warns = planning.check(plan)
    for e in errs:
        out("오류: " + e)
    for w in warns:
        out("경고: " + w)
    out("기획 검사: 오류 %d, 경고 %d" % (len(errs), len(warns)))
    if errs:
        raise SystemExit(1)


def cmd_recommend(proj, a):
    plan = planning.ensure(copy.deepcopy(proj.series))
    recs = planning.recommend(plan)
    mix = plan["format_mix"]
    out("추천 포맷 상위 %d (목적 %s, KPI %s)" % (len(recs), plan["purpose"], ", ".join(plan["kpi"]) or "기본값"))
    for i, (fid, score, why) in enumerate(recs, 1):
        f = formats.get(fid)
        out("%d. %s (%s) 점수 %d — %s" % (i, fid, f["name"], score, " ".join(why)))
        out("   현재 format_mix: %s" % ("포함" if fid in mix else "없음"))
    ids = [r[0] for r in recs]
    missing = [f for f in ids if f not in mix]
    extra = [f for f in mix if f not in ids]
    if missing:
        out("format_mix 에 넣어 볼 만한 추천 포맷: %s" % ", ".join(missing))
    if extra:
        out("추천 밖이지만 현재 조합에 있는 포맷: %s (의도한 것이면 그대로 둬도 됩니다)" % ", ".join(extra))
    if not mix:
        out("format_mix 가 비어 있습니다. 예: toon plan set --format-mix %s" % ",".join(ids[:3]))


def cmd_approve(proj, a):
    plan = planning.ensure(proj.series)
    planning.approve(plan)
    proj.save_series()
    out("기획을 승인했습니다(%s). 다음: 그림체(toon style presets)." % plan["approved_at"])


def run(proj, a):
    {"show": cmd_show, "set": cmd_set, "pillar": cmd_pillar, "check": cmd_check,
     "recommend": cmd_recommend, "approve": cmd_approve}[a.pl](proj, a)
