import json
import os

from . import formats, schema
from .util import ToonError, check_id, find_root, now, read_json, write_json, FONT_DIR

DEFAULT_FONTS = {
    "title": "Pretendard-Black.otf",
    "dialogue": "Pretendard-Bold.otf",
    "caption": "Pretendard-SemiBold.otf",
    "handwriting": "NanumPenScript-Regular.ttf",
}


class Project:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.series = read_json(os.path.join(self.root, "series.json"))

    @classmethod
    def open(cls, root=None):
        return cls(find_root(root, explicit=root is not None))

    def resolve(self, p):
        """저장된 경로를 절대 경로로. 옛 데이터의 절대 경로도 그대로 읽는다."""
        return p if os.path.isabs(p) else os.path.join(self.root, p)

    def save_series(self):
        write_json(os.path.join(self.root, "series.json"), self.series)

    def style_bible(self):
        """style.bible 이 있으면 그것, 비면 옛 style_bible."""
        st = self.series.get("style") or {}
        return (st.get("bible") or "").strip() or (self.series.get("style_bible") or "").strip()

    def approved_sample(self):
        st = self.series.get("style") or {}
        f = st.get("approved_sample")
        if not f:
            return None
        p = self.resolve(f)
        return p if os.path.isfile(p) else None

    def store_path(self, p):
        """시리즈 루트 안의 경로는 상대 경로로 저장한다. 밖의 경로는 절대 경로 그대로."""
        ap = os.path.abspath(self.resolve(p))
        if ap == self.root or ap.startswith(self.root + os.sep):
            return os.path.relpath(ap, self.root)
        return ap

    def valid_storyboard(self, ep):
        """검증을 통과한 (storyboard, 경고 목록). 오류가 있으면 ToonError."""
        sb = self.load_storyboard(ep)
        try:
            fmt = formats.get(self.load_episode(ep).get("format"))
        except (OSError, ValueError, ToonError):
            fmt = None
        errs, warns = schema.check_storyboard(sb, set(self.char_ids()), fmt)
        errs = schema.check_series(self.series) + errs
        if errs:
            raise ToonError("콘티 검증 실패:\n  " + "\n  ".join(errs))
        return sb, warns

    @property
    def canvas(self):
        c = self.series.get("canvas") or [1080, 1350]
        return int(c[0]), int(c[1])

    def font(self, role):
        name = (self.series.get("fonts") or {}).get(role) or DEFAULT_FONTS[role]
        for cand in (name, os.path.join(self.root, name), os.path.join(FONT_DIR, name)):
            if os.path.isfile(cand):
                return os.path.abspath(cand)
        raise ToonError("폰트 파일을 찾을 수 없습니다(%s): %s" % (role, name))

    def ep_dir(self, n):
        return os.path.join(self.root, "episodes", "ep%02d" % n)

    def page_dir(self, ep, n):
        return os.path.join(self.ep_dir(ep), "pages", "p%02d" % n)

    def char_dir(self, cid):
        return os.path.join(self.root, "characters", check_id(cid, "캐릭터 id"))

    def char_ids(self):
        base = os.path.join(self.root, "characters")
        if not os.path.isdir(base):
            return []
        return sorted(d for d in os.listdir(base)
                      if os.path.isfile(os.path.join(base, d, "character.json")))

    def load_char(self, cid):
        return read_json(os.path.join(self.char_dir(cid), "character.json"))

    def save_char(self, cid, data):
        write_json(os.path.join(self.char_dir(cid), "character.json"), data)

    def approved_sheet(self, cid):
        c = self.load_char(cid)
        f = c.get("approved_sheet")
        if not f:
            return None
        p = os.path.join(self.char_dir(cid), f)
        return p if os.path.isfile(p) else None

    def load_storyboard(self, ep):
        return read_json(os.path.join(self.ep_dir(ep), "storyboard.json"))

    def load_episode(self, ep):
        return read_json(os.path.join(self.ep_dir(ep), "episode.json"))

    def page_json_path(self, ep, n):
        return os.path.join(self.page_dir(ep, n), "page.json")

    def page_json(self, ep, n):
        p = self.page_json_path(ep, n)
        if os.path.isfile(p):
            return read_json(p)
        return {"n": n, "versions": [], "chosen": None, "approved": False, "status": "pending"}

    def save_page_json(self, ep, n, data):
        write_json(self.page_json_path(ep, n), data)

    def chosen_file(self, ep, n, pj=None):
        pj = pj or self.page_json(ep, n)
        vs = pj.get("versions") or []
        ch = pj.get("chosen")
        if ch is None and vs:
            ok = [v for v in vs if not v.get("rejected")]
            if ok:
                ch = ok[-1]["v"]
        if ch is None:
            return None, None
        for v in vs:
            if v["v"] == ch:
                return ch, os.path.join(self.page_dir(ep, n), v["file"])
        return None, None

    def no_image_hint(self, ep, n):
        vs = self.page_json(ep, n).get("versions") or []
        if vs and all(v.get("rejected") for v in vs):
            return "모든 버전이 rejected 입니다. toon ingest 로 새 이미지를 등록하세요."
        return "등록된 이미지 버전이 없습니다(toon ingest 먼저)."

    def require_usable(self, ep, n, pj=None):
        """쓸 수 있는 채택 버전 (v, 경로). rejected 이거나 없으면 ToonError."""
        pj = pj or self.page_json(ep, n)
        v, src = self.chosen_file(ep, n, pj)
        if not src:
            raise ToonError("%d장: %s" % (n, self.no_image_hint(ep, n)))
        for x in pj.get("versions") or []:
            if x["v"] == v and x.get("rejected"):
                raise ToonError("%d장: 채택된 v%s 는 rejected 라 쓸 수 없습니다. toon ingest 로 새 버전을 등록하세요." % (n, v))
        return v, src

    def stale_problems(self, ep, n, pj=None):
        """lettered.png 가 현재 채택 버전과 letter.json 을 반영하는지. 문제 목록(비어 있으면 최신)."""
        redo = "toon letter 를 다시 실행하세요."
        pd = self.page_dir(ep, n)
        lt = os.path.join(pd, "lettered.png")
        meta = os.path.join(pd, "lettered.json")
        if not os.path.isfile(lt) or not os.path.isfile(meta):
            return ["%d장: lettered.png 가 없습니다. %s" % (n, redo)]
        v, _ = self.chosen_file(ep, n, pj)
        try:
            rep = read_json(meta)
            lv = rep.get("version") if isinstance(rep, dict) else None
        except ToonError:
            lv = None
        if lv != v:
            return ["%d장: lettered.png 는 v%s 기준인데 채택 버전은 v%s 입니다. %s" % (n, lv, v, redo)]
        lp = os.path.join(pd, "letter.json")
        if os.path.isfile(lp) and os.path.getmtime(lt) + 1e-6 < os.path.getmtime(lp):
            return ["%d장: letter.json 이 lettered.png 보다 새롭습니다. %s" % (n, redo)]
        return []

    def log(self, **row):
        row = dict(ts=now(), **row)
        with open(os.path.join(self.root, "ledger.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def ledger(self):
        p = os.path.join(self.root, "ledger.jsonl")
        rows = []
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except ValueError:
                            pass
        return rows

