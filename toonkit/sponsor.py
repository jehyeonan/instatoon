"""광고 표기(sponsored 설정) 검사와 캡션 처리."""
import re

from . import formats

DEFAULT_LABEL = "광고"
_BAD_EN = re.compile(r"(?<![A-Za-z])(ad|pr|sponsored)(?![A-Za-z])", re.I)
_BAD_X = re.compile(r"×|(?<![A-Za-z])[xX](?![A-Za-z])")


def settings(epj):
    """정규화된 sponsored 설정 dict 또는 None."""
    s = epj.get("sponsored")
    if not s:
        return None
    if s is True:
        s = {}
    label = str(s.get("label") or DEFAULT_LABEL).strip()
    return {"label": label, "cover_chip": s.get("cover_chip", True) is not False,
            "all_pages": bool(s.get("all_pages", False))}


def hashtag(label):
    return "#" + re.sub(r"\s+", "", label)


def caption_text(epj):
    """caption.txt 본문(해시태그 줄 제외). sponsored 이면 첫 줄에 #라벨 을 보장한다."""
    cap = (epj.get("caption") or "").strip()
    s = settings(epj)
    if s:
        tag = hashtag(s["label"])
        first = cap.split("\n", 1)[0] if cap else ""
        if tag not in first:
            cap = tag + ("\n" + cap if cap else "")
    return cap


def check(epj):
    """에피소드 단위 광고 표기 오류 목록."""
    errors = []
    f = formats.get(epj.get("format"))
    s = settings(epj)
    if f and f["sponsored"] and not s:
        errors.append("광고 표기 설정 필요: episode.json 에 sponsored(label, cover_chip, all_pages)를 넣으세요.")
    if not s:
        return errors
    first = (epj.get("caption") or "").strip().split("\n", 1)[0]
    for what, text in (("label", s["label"]), ("캡션 첫 줄", first)):
        if "체험단" in text:
            errors.append("광고 표기: %s 에 '체험단' 은 쓸 수 없습니다(광고, 유료광고, 상품 협찬 등 대가에 맞는 한글 표기)." % what)
        if _BAD_EN.search(text):
            errors.append("광고 표기: %s 에 AD, PR, Sponsored 같은 영문 표기를 쓰지 마세요: %r" % (what, text))
        if _BAD_X.search(text) and "협찬받음" not in text:
            errors.append("광고 표기: %s 의 ×/x 만 쓴 표기는 광고 표시로 인정되지 않습니다: %r" % (what, text))
    return errors

