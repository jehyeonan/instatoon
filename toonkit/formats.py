"""콘티 포맷 레지스트리. references/formats.md 의 16개 포맷과 같은 내용을 데이터로 둔다."""
from .util import ToonError

HARD_MAX_PAGES = 20

# roles: (최소 장 수, 최대 장 수, 역할). 고정 장은 (1, 1, ...), 범위 장은 한 줄로 두고 장 수만 늘린다.
_F = []


def _add(id, name, summary, tags, pages, ending, roles, sponsored=False):
    _F.append({"id": id, "name": name, "summary": summary, "tags": tags, "pages": pages,
               "ending_type": ending, "sponsored": sponsored, "roles": roles})


_add("ranking", "랭킹형", "항목을 순서대로 보여 주고 마지막에 반전이나 공감 한마디", ["저장", "공유"], (6, 10), "series", [
    (1, 1, "표지: 제목 3줄(가운데 강조) + 주인공 상반신"), (1, 1, "왜 이 순위를 매기게 됐는지"),
    (1, 1, "3위"), (1, 1, "2위, 3위보다 강한 반응"), (1, 1, "1위 공개 직전 뜸 들이기"),
    (1, 1, "1위, 가장 큰 컷"), (1, 1, "반전 또는 저장하고 싶은 팁 한 줄"), (1, 1, "엔딩: 마무리 컷")])
_add("anecdote", "일화형", "내가 겪은 작은 사건 하나를 웃음이나 공감 한 줄로 닫는 일상툰", ["공감", "웃음"], (6, 8), "series", [
    (1, 1, "표지: 결과를 암시하는 제목"), (1, 1, "상황 설정"), (2, 2, "사건 전개"),
    (1, 1, "당황·반전"), (1, 1, "깨달음이나 웃음 한 줄"), (1, 1, "엔딩")])
_add("kishotenketsu", "기승전결 확장형", "4컷 기승전결을 컷당 1~2장으로 늘려 전에서 예상을 비튼다", ["공감", "웃음"], (7, 10), "series", [
    (1, 1, "표지"), (1, 1, "기: 상황 한눈에"), (2, 2, "승: 기대를 키움"),
    (2, 2, "전: 예측을 흔듦"), (1, 1, "결: 펀치라인 또는 여운"), (1, 1, "엔딩")])
_add("punchline", "셋업-펀치라인형", "같은 구도를 세 번 반복해 리듬을 만들고 네 번째에 깬다", ["웃음", "공감"], (6, 8), "series", [
    (1, 1, "표지: 반복될 행동 암시"), (3, 3, "같은 구도 3회 반복"), (1, 1, "깨짐"),
    (1, 1, "정적 컷이나 여운"), (1, 1, "엔딩")])
_add("comparison", "상황극 비교형", "한 인물이 상황·상대에 따라 달라지는 모습을 쌍으로 보여 준다", ["공감", "웃음"], (6, 9), "series", [
    (1, 1, "표지: A vs B"), (2, 4, "쌍 (장마다 위 A / 아래 B)"), (1, 1, "가장 극단적인 쌍"),
    (1, 1, "한 줄 결론 + 엔딩")])
_add("expectation", "기대 vs 현실", "기대 컷과 현실 컷을 한 쌍씩 보여 준다", ["공감", "웃음"], (6, 9), "series", [
    (1, 1, "표지: 기대 vs 현실"), (2, 5, "장마다 위 기대 / 아래 현실"),
    (1, 1, "가장 큰 간극 또는 위로 한 줄"), (1, 1, "엔딩")])
_add("explainer", "문제-원인-해결 정보툰", "고민을 짚고 원인을 설명한 뒤 해결을 단계로 푼다", ["저장", "정보"], (6, 10), "cta", [
    (1, 1, "표지: 질문형 제목"), (1, 1, "공감: 흔한 오해·실수 장면"), (1, 1, "원인"),
    (1, 3, "해결 (장당 하나)"), (1, 1, "요약 한 장 (저장용)"), (1, 1, "엔딩: 행동 하나")])
_add("checklist", "체크리스트형", "번호 항목을 장마다 하나씩, 마지막에 한 장 요약", ["저장", "정보"], (6, 9), "cta", [
    (1, 1, "표지: N가지"), (1, 1, "왜 필요한가"), (3, 5, "항목 (장마다 하나)"), (1, 1, "요약 + 엔딩")])
_add("beforeafter", "비포/애프터", "전후를 먼저 대비하고 바뀐 과정을 푼다", ["저장", "정보"], (6, 9), "cta", [
    (1, 1, "표지: 전→후 한 장 대비"), (1, 1, "전의 고민"), (2, 3, "바뀐 과정"),
    (1, 1, "후 결과"), (1, 1, "요약"), (1, 1, "엔딩: 저장 유도")])
_add("typecompare", "유형 비교형", "같은 상황에서 유형별 반응을 보여 줘 댓글을 부른다", ["댓글", "공감"], (6, 9), "cta", [
    (1, 1, "표지: 상황 + 유형 수"), (1, 1, "상황 제시"), (2, 4, "유형별 반응 (장당 2~4유형)"),
    (1, 1, "가장 극단적인 유형"), (1, 1, "엔딩: 너는 무슨 유형?")])
_add("serial", "사연·제보 연재형", "독자 제보를 각색해 여러 화로 나누고 매 화 끝에서 끊는다", ["팔로우", "정주행"], (8, 20), "continue", [
    (1, 1, "표지: 제목 + 화 번호·부제 칩 + 각색 고지"), (2, 2, "인물·관계 소개"), (2, 14, "갈등 확대 (장마다 컷 2개, 내레이션 띠)"),
    (1, 1, "가장 센 장면"), (1, 1, "끊기: - 계속 - 또는 다음 화 미리보기")])
_add("episodic", "세계관 에피소드형", "고정 캐릭터로 매 화 독립 에피소드, 다음 화 떡밥 하나", ["팔로우", "정주행"], (6, 10), "continue", [
    (1, 1, "표지: 시리즈명 + ep 번호 + 첫 장면"), (4, 8, "상황 → 사건 → 반전 (장당 컷 3~4개)"),
    (1, 1, "캐릭터 마무리 컷 + 다음 화 한 줄")])
_add("reader", "독자 참여형", "독자의 요청이나 질문을 골라 그려 답하는 짧은 편", ["댓글", "참여"], (5, 7), "cta", [
    (1, 1, "표지: 요청 댓글 인용"), (1, 2, "사연 요약과 상황"), (1, 1, "그림 답변이나 위로"),
    (1, 1, "마무리 + 다음 사연은 댓글로")])
_add("quiz", "퀴즈·선택형", "표지에서 문제, 다음 장에서 정답", ["댓글", "참여"], (6, 9), "cta", [
    (1, 1, "표지: 문제"), (1, 1, "보기 2~3개"), (1, 1, "정답은 다음 장"), (1, 1, "정답"),
    (1, 2, "해설"), (1, 1, "함정·오답 이유"), (1, 1, "엔딩: 몇 개 맞혔는지 댓글")])
_add("sponsored", "협찬 공감 해결형", "공감 상황에서 시작해 제품이 해결 도구로 늦게 등장하는 브랜디드툰", ["협찬"], (7, 9), "series", [
    (1, 1, "표지: 상황 제목 + 광고 표기"), (1, 1, "독자가 겪어 봤을 상황"), (2, 3, "문제가 커지는 과정"),
    (1, 1, "전환: 제품이 처음 등장 (6장 이후)"), (1, 1, "달라진 장면과 웃음"), (1, 1, "작가 한 줄 후기 + 광고 표기")], True)
_add("groupbuy", "공구·이벤트 연동형", "협찬 이야기 뒤에 혜택과 참여 방법 장을 붙인다", ["협찬", "공구"], (8, 10), "cta", [
    (1, 1, "표지: 상황 제목 + 광고 표기"), (1, 1, "독자가 겪어 봤을 상황"), (1, 3, "문제가 커지는 과정"),
    (1, 1, "전환: 제품이 처음 등장"), (1, 1, "달라진 장면과 웃음"), (1, 1, "혜택: 가격, 구성, 사은품"),
    (1, 1, "방법과 기한 + 광고 표기"), (1, 1, "엔딩: 작가 한마디")], True)

FORMATS = dict((f["id"], f) for f in _F)
ORDER = [f["id"] for f in _F]


def get(fid):
    return FORMATS.get(fid)


def require(fid):
    f = FORMATS.get(fid)
    if f is None:
        raise ToonError("알 수 없는 포맷 '%s'. 사용 가능: %s (toon formats 로 목록 확인)" % (fid, ", ".join(ORDER)))
    return f


def role_counts(f, target=None):
    """역할별 장 수. 합이 target(기본: 권장 범위 중간값)이 되도록 각 역할의 허용 폭 안에서 늘린다."""
    lo, hi = f["pages"]
    target = (lo + hi) // 2 if target is None else target
    counts = [r[0] for r in f["roles"]]
    total = sum(counts)
    for i, r in enumerate(f["roles"]):
        while total < target and counts[i] < r[1]:
            counts[i] += 1
            total += 1
    return counts


def expand_roles(f, target=None):
    out = []
    for c, r in zip(role_counts(f, target), f["roles"]):
        out += [r[2]] * c
    return out


def role_lines(f):
    """표시용 (장 범위, 역할). 범위 장은 한 줄로, 위치는 기본 장 수 기준."""
    rows, pos = [], 1
    for c, r in zip(role_counts(f), f["roles"]):
        end = pos + c - 1
        rows.append((str(pos) if c == 1 else "%d~%d" % (pos, end), r[2]))
        pos = end + 1
    return rows


def storyboard_template(f):
    roles = expand_roles(f)
    pages = []
    for i, role in enumerate(roles, 1):
        kind = "cover" if i == 1 else "ending" if i == len(roles) else "body"
        p = {"n": i, "kind": kind, "scene": "TODO [%s] %s" % (f["id"], role), "cast": [], "lines": [], "in_image_text": []}
        if kind == "cover":
            p["cover_title"] = ["TODO", "TODO", "TODO"]
        pages.append(p)
    return {"pages": pages}


def check_pages(f, count):
    """권장 범위 밖이면 경고 문자열."""
    lo, hi = f["pages"]
    if count < lo or count > hi:
        return "장 수가 %d장입니다(%s 포맷 권장 %d~%d장)." % (count, f["id"], lo, hi)
    return None


def format_table():
    rows = ["%-14s %-18s %-7s %-9s %s" % ("id", "이름", "장 수", "엔딩", "한 줄 설명")]
    for fid in ORDER:
        f = FORMATS[fid]
        rows.append("%-14s %-18s %-7s %-9s %s%s" % (fid, f["name"], "%d~%d" % f["pages"], f["ending_type"], f["summary"],
                                                   " [광고 표기 필요]" if f["sponsored"] else ""))
    return "\n".join(rows)


def format_detail(f):
    out = ["%s — %s" % (f["id"], f["name"]), f["summary"],
           "목적: %s / 권장 %d~%d장 / 엔딩: %s%s" % (", ".join(f["tags"]), f["pages"][0], f["pages"][1], f["ending_type"],
                                              " / 광고 표기 필요" if f["sponsored"] else ""), ""]
    for span, text in role_lines(f):
        out.append("  %s장  %s" % (span, text))
    return "\n".join(out)

