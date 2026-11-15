"""시리즈 기획(plan): 검증, 포맷 추천, 승인 (정지점 P)."""
import copy
import re

from . import formats
from .util import ToonError, now

PURPOSES = {
    "growth": "계정 키우기(팔로워·도달)",
    "brand": "개인·회사 브랜딩, 전문성 알리기",
    "monetize": "협찬·공구·상품으로 수익",
    "portfolio": "작품 포트폴리오, 작가로서의 이력",
    "record": "일상·경험 기록, 소통",
}
KPIS = ("saves", "shares", "follows", "comments", "clicks")
MONETIZATIONS = ("none", "sponsored", "groupbuy", "goods", "lecture", "subscription")

# 목적별 추천 포맷(우선순위 순), 기본 KPI, 이유
PURPOSE_REC = {
    "growth": (["anecdote", "comparison", "expectation", "punchline", "typecompare"], ["shares", "follows"],
               "공감과 공유가 잘 되는 짧은 이야기가 새 독자를 데려온다."),
    "brand": (["explainer", "ranking", "checklist", "episodic"], ["saves", "follows"],
              "저장할 만한 정보형이 전문성을 보여 주고, 연재로 기억에 남긴다."),
    "monetize": (["ranking", "explainer", "sponsored", "groupbuy", "episodic"], ["saves", "clicks"],
                 "저장·클릭으로 이어지는 정보형과 협찬·공구 포맷이 수익 연결이 쉽다."),
    "portfolio": (["kishotenketsu", "punchline", "episodic", "beforeafter"], ["shares"],
                  "연출과 반전이 드러나는 포맷이 작가의 실력을 보여 준다."),
    "record": (["anecdote", "episodic", "serial"], ["comments", "follows"],
               "경험담과 연재는 소통과 단골 독자를 만든다."),
}
KPI_REC = {
    "saves": (["explainer", "checklist", "ranking"], "나중에 다시 볼 정보라서 저장이 늘기 쉽다."),
    "shares": (["comparison", "expectation", "typecompare"], "친구에게 보내고 싶은 공감 소재라서 공유가 늘기 쉽다."),
    "follows": (["serial", "episodic"], "다음 화가 궁금해야 팔로우한다."),
    "comments": (["typecompare", "reader", "quiz"], "독자가 답하고 싶어지는 형식이다."),
    "clicks": (["sponsored", "groupbuy"], "제품·구매 링크로 이어지는 형식이다."),
}


def empty_plan():
    return {
        "purpose": "", "purpose_note": "",
        "audience": {"who": "", "pain": "", "want": ""},
        "premise": "", "pillars": [], "tone": "", "cadence": "",
        "format_mix": [], "kpi": [], "monetization": [],
        "boundaries": [], "references": [],
        "approved": False, "approved_at": None,
    }


def get(series):
    """plan 객체(없으면 None)."""
    p = series.get("plan")
    return p if isinstance(p, dict) else None


def ensure(series):
    p = get(series)
    if p is None:
        p = empty_plan()
        series["plan"] = p
        return p
    base = empty_plan()
    for k, v in base.items():
        p.setdefault(k, v)
    if not isinstance(p["audience"], dict):
        p["audience"] = dict(base["audience"])
    for k in base["audience"]:
        p["audience"].setdefault(k, "")
    return p


def is_approved(series):
    p = get(series)
    return bool(p and p.get("approved"))


def content(plan):
    """승인 여부를 뺀 내용(변경 감지용)."""
    c = copy.deepcopy(plan)
    c.pop("approved", None)
    c.pop("approved_at", None)
    return c


def split_terms(s):
    return [t.strip() for t in re.split(r"[,/·]", s or "") if len(t.strip()) >= 2]


def check(plan):
    """(errors, warnings)."""
    errs, warns = [], []
    purpose = plan.get("purpose")
    if not purpose:
        errs.append("purpose(주 목적)가 없습니다. 선택: %s" % ", ".join(PURPOSES))
    elif purpose not in PURPOSES:
        errs.append("purpose '%s' 는 %s 중 하나여야 합니다." % (purpose, ", ".join(PURPOSES)))
    if not str(plan.get("premise") or "").strip():
        errs.append("premise(한 줄 시리즈 소개)가 없습니다.")
    if not str((plan.get("audience") or {}).get("who") or "").strip():
        errs.append("audience.who(누구에게 보여 줄지)가 없습니다.")
    pillars = plan.get("pillars") or []
    if not 3 <= len(pillars) <= 5:
        errs.append("콘텐츠 기둥(pillars)은 3~5개여야 합니다(지금 %d개)." % len(pillars))
    total = 0
    for p in pillars:
        sh = p.get("share", 0)
        total += sh if isinstance(sh, (int, float)) and not isinstance(sh, bool) else 0
    if pillars and abs(total - 100) > 1:
        errs.append("기둥 share 합이 %s 입니다(100이어야 함, ±1 허용)." % total)
    mix = plan.get("format_mix") or []
    for fid in mix:
        if formats.get(fid) is None:
            errs.append("format_mix 에 모르는 포맷 id '%s' (toon formats 로 확인)." % fid)
    kpi = plan.get("kpi") or []
    if not 1 <= len(kpi) <= 2:
        errs.append("kpi 는 1~2개여야 합니다(지금 %d개). 선택: %s" % (len(kpi), ", ".join(KPIS)))
    for k in kpi:
        if k not in KPIS:
            errs.append("kpi '%s' 는 %s 중 하나여야 합니다." % (k, ", ".join(KPIS)))
    mon = plan.get("monetization") or []
    for m in mon:
        if m not in MONETIZATIONS:
            errs.append("monetization '%s' 는 %s 중 하나여야 합니다." % (m, ", ".join(MONETIZATIONS)))
    for m in ("sponsored", "groupbuy"):
        if m in mon and m not in mix:
            warns.append("monetization 에 %s 가 있는데 format_mix 에 %s 포맷이 없습니다." % (m, m))
    if purpose == "monetize" and (not mon or mon == ["none"]):
        warns.append("purpose 가 monetize 인데 monetization 이 none(또는 비어 있음)입니다.")
    return errs, warns


def recommend(plan, limit=5):
    """[(포맷 id, 점수, [이유...])] 점수 내림차순 상위 limit개."""
    purpose = plan.get("purpose")
    if purpose not in PURPOSE_REC:
        raise ToonError("먼저 목적을 정하세요: toon plan set --purpose %s" % "|".join(PURPOSES))
    base, default_kpi, why = PURPOSE_REC[purpose]
    kpi = [k for k in (plan.get("kpi") or []) if k in KPI_REC] or default_kpi
    score, reasons = {}, {}
    for i, fid in enumerate(base):
        score[fid] = score.get(fid, 0) + 10 - i
        reasons.setdefault(fid, []).append("목적 %s: %s" % (purpose, why))
    for k in kpi:
        fids, kwhy = KPI_REC[k]
        for fid in fids:
            score[fid] = score.get(fid, 0) + 4
            reasons.setdefault(fid, []).append("KPI %s: %s" % (k, kwhy))
    order = list(base) + [f for k in kpi for f in KPI_REC[k][0] if f not in base]
    order = list(dict.fromkeys(order))
    ranked = sorted(order, key=lambda f: (-score[f], order.index(f)))
    return [(f, score[f], reasons[f]) for f in ranked[:limit]]


def approve(plan):
    errs, _ = check(plan)
    if errs:
        raise ToonError("기획 검사 오류가 %d개 있어 승인할 수 없습니다:\n  " % len(errs) + "\n  ".join(errs))
    plan["approved"] = True
    plan["approved_at"] = now()


def status_line(series):
    p = get(series)
    if p is None:
        return "기획: 없음(옛 시리즈). toon plan show 로 기획부터 정하세요."
    return "기획: 목적 %s, 기둥 %d개, %s" % (p.get("purpose") or "미정", len(p.get("pillars") or []),
                                         "승인됨" if p.get("approved") else "승인 안 됨")


def boundary_hits(plan, texts):
    """plan.boundaries 의 금지어(쉼표·슬래시로 여러 개 가능)가 texts 에 나오면 [(금지어, 문자열)]."""
    hits = []
    terms = [t for b in (plan or {}).get("boundaries") or [] for t in split_terms(b)]
    for t in terms:
        for s in texts:
            if t in s:
                hits.append((t, s))
                break
    return hits


def pillar_distribution(series, epjs):
    """기획 share 와 에피소드 pillar 분포 비교 줄(없으면 None)."""
    p = get(series)
    if not p or not p.get("pillars"):
        return None
    tagged = [e.get("pillar") for e in epjs if e.get("pillar")]
    if not tagged:
        return None
    ids = [pl["id"] for pl in p["pillars"]]
    parts = []
    for pl in p["pillars"]:
        n = tagged.count(pl["id"])
        parts.append("%s %d편 %.0f%%/목표 %s%%" % (pl["id"], n, n * 100.0 / len(tagged), pl.get("share", 0)))
    line = "기둥 분포: " + ", ".join(parts)
    extra = len([t for t in tagged if t not in ids])
    if extra:
        line += ", 기획에 없는 기둥 %d편" % extra
    if len(epjs) - len(tagged):
        line += " (기둥 미지정 %d편)" % (len(epjs) - len(tagged))
    return line
