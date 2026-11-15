import json
import os
import shutil
import tempfile
import unittest

import helpers

from test_review import Base
from toonkit import planning


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def jsave(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)


class FreshBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="toonplan_")
        self.root = os.path.join(self.dir, "s")
        code, o, e = helpers.toon("init", self.root, "--title", "테스트툰")
        assert code == 0, e
        self.png = helpers.make_image(os.path.join(self.dir, "good.png"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def t(self, *a):
        return helpers.toon("--root", self.root, *a)

    def plan(self):
        return jload(os.path.join(self.root, "series.json"))["plan"]

    def fill(self):
        """검사를 통과하는 기획을 채운다(승인은 하지 않음)."""
        self.assertEqual(self.t("plan", "set", "--purpose", "growth", "--premise", "한 줄 소개", "--who", "20대 직장인",
                                "--kpi", "shares", "--format-mix", "anecdote,comparison")[0], 0)
        for name, share in (("가", 40), ("나", 30), ("다", 30)):
            self.assertEqual(self.t("plan", "pillar", "add", name, "--share", str(share))[0], 0)


class PlanDataTests(FreshBase):
    def test_init_has_empty_unapproved_plan(self):
        p = self.plan()
        self.assertFalse(p["approved"])
        self.assertIsNone(p["approved_at"])
        self.assertEqual(p["pillars"], [])
        self.assertEqual(set(p["audience"]), {"who", "pain", "want"})

    def test_set_and_show(self):
        code, o, e = self.t("plan", "set", "--purpose", "brand", "--premise", "소개", "--tone", "다정", "--cadence", "주 2회",
                            "--who", "누구", "--pain", "고민", "--want", "웃음", "--kpi", "saves,follows",
                            "--monetization", "lecture", "--format-mix", "explainer,ranking",
                            "--boundary", "정치", "--boundary", "실명", "--reference", "계정A")
        self.assertEqual(code, 0, e)
        p = self.plan()
        self.assertEqual((p["purpose"], p["tone"], p["cadence"]), ("brand", "다정", "주 2회"))
        self.assertEqual(p["audience"], {"who": "누구", "pain": "고민", "want": "웃음"})
        self.assertEqual(p["kpi"], ["saves", "follows"])
        self.assertEqual(p["format_mix"], ["explainer", "ranking"])
        self.assertEqual(p["boundaries"], ["정치", "실명"])
        code, o, e = self.t("plan", "show")
        self.assertEqual(code, 0, e)
        self.assertIn("브랜딩", o)
        self.assertIn("(비어 있음)", o)  # 기둥 등 빈 칸

    def test_set_rejects_bad_purpose_and_empty(self):
        self.assertEqual(self.t("plan", "set", "--purpose", "fame")[0], 2)
        self.assertEqual(self.t("plan", "set")[0], 2)

    def test_set_file_merges(self):
        self.t("plan", "set", "--who", "원래")
        f = os.path.join(self.dir, "plan.json")
        jsave(f, {"purpose": "record", "audience": {"pain": "고민만"}, "approved": True,
                  "pillars": [{"id": "p1", "name": "a", "desc": "", "share": 100}]})
        self.assertEqual(self.t("plan", "set", "--file", f)[0], 0)
        p = self.plan()
        self.assertEqual(p["purpose"], "record")
        self.assertEqual(p["audience"]["who"], "원래")
        self.assertEqual(p["audience"]["pain"], "고민만")
        self.assertEqual(len(p["pillars"]), 1)
        self.assertFalse(p["approved"])  # 파일로 승인할 수 없다

    def test_pillar_add_rm(self):
        self.t("plan", "pillar", "add", "첫째", "--desc", "설명", "--share", "50")
        self.t("plan", "pillar", "add", "둘째", "--share", "50")
        self.assertEqual([x["id"] for x in self.plan()["pillars"]], ["p1", "p2"])
        self.assertEqual(self.t("plan", "pillar", "rm", "p1")[0], 0)
        self.t("plan", "pillar", "add", "셋째")
        self.assertEqual([x["id"] for x in self.plan()["pillars"]], ["p2", "p3"])
        self.assertEqual(self.t("plan", "pillar", "rm", "p9")[0], 2)


class PlanCheckTests(FreshBase):
    def errs(self):
        code, o, e = self.t("plan", "check")
        return code, o

    def test_empty_plan_errors(self):
        code, o = self.errs()
        self.assertEqual(code, 1)
        for w in ("purpose", "premise", "audience.who", "기둥", "kpi"):
            self.assertIn(w, o)

    def test_valid_plan_passes(self):
        self.fill()
        code, o = self.errs()
        self.assertEqual(code, 0, o)
        self.assertIn("오류 0", o)

    def test_each_error(self):
        self.fill()
        self.t("plan", "pillar", "rm", "p3")
        self.assertIn("3~5개", self.errs()[1])
        self.t("plan", "pillar", "add", "다", "--share", "10")
        code, o = self.errs()
        self.assertIn("share 합이 80", o)
        self.t("plan", "pillar", "rm", "p3")
        self.t("plan", "pillar", "add", "다", "--share", "31")  # 101: 허용
        self.assertEqual(self.errs()[0], 0)
        self.t("plan", "set", "--format-mix", "anecdote,nope")
        self.assertIn("모르는 포맷 id 'nope'", self.errs()[1])
        self.t("plan", "set", "--format-mix", "anecdote", "--kpi", "saves,shares,clicks")
        self.assertIn("1~2개", self.errs()[1])
        self.t("plan", "set", "--kpi", "shares", "--who", "")
        self.assertIn("audience.who", self.errs()[1])

    def test_warnings(self):
        self.fill()
        self.t("plan", "set", "--purpose", "monetize")
        code, o = self.errs()
        self.assertEqual(code, 0)
        self.assertIn("monetization 이 none", o)
        self.t("plan", "set", "--monetization", "sponsored,groupbuy")
        code, o = self.errs()
        self.assertEqual(code, 0)
        self.assertIn("sponsored 포맷이 없습니다", o)
        self.assertIn("groupbuy 포맷이 없습니다", o)

    def test_example_plan_passes(self):
        errs, warns = planning.check(jload(os.path.join(helpers.EXAMPLE, "series.json"))["plan"])
        self.assertEqual((errs, warns), ([], []))


class PlanRecommendTests(FreshBase):
    def test_requires_purpose(self):
        self.assertEqual(self.t("plan", "recommend")[0], 2)

    def test_purpose_and_kpi_ranking(self):
        recs = planning.recommend({"purpose": "monetize", "kpi": ["saves", "clicks"], "format_mix": []})
        ids = [r[0] for r in recs]
        self.assertEqual(len(ids), 5)
        self.assertEqual(ids[0], "ranking")  # 목적 1순위 + saves 보정
        self.assertIn("sponsored", ids)
        self.assertTrue(all(r[2] for r in recs))
        recs = planning.recommend({"purpose": "record", "kpi": ["comments"]})
        self.assertIn("typecompare", [r[0] for r in recs])  # KPI 보정으로 추가

    def test_command_compares_with_mix(self):
        self.t("plan", "set", "--purpose", "growth", "--kpi", "shares", "--format-mix", "anecdote,quiz")
        code, o, e = self.t("plan", "recommend")
        self.assertEqual(code, 0, e)
        self.assertIn("anecdote (일화형) 점수 10", o)
        self.assertIn("포함", o)
        self.assertIn("없음", o)
        self.assertIn("추천 밖이지만 현재 조합에 있는 포맷: quiz", o)


class PlanApproveTests(FreshBase):
    def test_approve_requires_clean_check(self):
        code, o, e = self.t("plan", "approve")
        self.assertEqual(code, 2)
        self.assertIn("승인할 수 없습니다", e)
        self.assertFalse(self.plan()["approved"])

    def test_approve_and_release_on_change(self):
        self.fill()
        code, o, e = self.t("plan", "approve")
        self.assertEqual(code, 0, e)
        self.assertTrue(self.plan()["approved"])
        self.assertTrue(self.plan()["approved_at"])
        code, o, e = self.t("plan", "set", "--tone", "새 말투")
        self.assertEqual(code, 0, e)
        self.assertIn("승인을 해제", o)
        self.assertFalse(self.plan()["approved"])
        self.t("plan", "approve")
        self.t("plan", "set", "--tone", "새 말투")  # 같은 값이면 유지
        self.assertTrue(self.plan()["approved"])
        code, o, e = self.t("plan", "pillar", "add", "넷째", "--share", "0")
        self.assertIn("승인을 해제", o)
        self.assertFalse(self.plan()["approved"])

    def test_status_first_line(self):
        code, o, e = self.t("status")
        self.assertEqual(o.splitlines()[0], "기획: 목적 미정, 기둥 0개, 승인 안 됨")
        self.fill()
        self.t("plan", "approve")
        o = self.t("status")[1]
        self.assertEqual(o.splitlines()[0], "기획: 목적 growth, 기둥 3개, 승인됨")


class PlanGateTests(FreshBase):
    def test_style_prompt_and_ingest_rejected_before_plan(self):
        self.t("style", "set", "--preset", "bw_manga")
        code, o, e = self.t("style", "prompt")
        self.assertEqual(code, 2)
        self.assertIn("기획", e)
        code, o, e = self.t("style", "ingest", self.png)
        self.assertEqual(code, 2)
        self.assertIn("--no-plan", e)

    def test_no_plan_bypass(self):
        self.t("style", "set", "--preset", "bw_manga")
        self.assertEqual(self.t("style", "prompt", "--no-plan")[0], 0)
        self.assertEqual(self.t("style", "ingest", self.png, "--no-plan")[0], 0)

    def test_approved_plan_allows_style(self):
        self.fill()
        self.t("plan", "approve")
        self.t("style", "set", "--preset", "bw_manga")
        self.assertEqual(self.t("style", "prompt")[0], 0)

    def test_legacy_series_without_plan_only_warns(self):
        self.t("style", "set", "--preset", "bw_manga")
        self.t("style", "ingest", self.png, "--no-plan")
        self.assertEqual(self.t("style", "approve")[0], 0)
        p = os.path.join(self.root, "series.json")
        s = jload(p)
        del s["plan"]
        jsave(p, s)
        code, o, e = self.t("style", "prompt")
        self.assertEqual(code, 0, e)
        self.assertIn("기획(plan)이 없습니다", o)
        self.assertEqual(self.t("status")[1].splitlines()[0][:7], "기획: 없음(")

    def test_unapproved_plan_object_not_legacy(self):
        self.t("style", "set", "--preset", "bw_manga")
        self.t("style", "ingest", self.png, "--no-plan")
        self.t("style", "approve")
        self.assertEqual(self.t("style", "prompt")[0], 2)  # plan 객체가 있으면 승인 필요


class EpisodePlanTests(Base):
    def epj(self, n):
        return jload(os.path.join(self.root, "episodes/ep%02d/episode.json" % n))

    def test_default_format_is_mix_first(self):
        p = os.path.join(self.root, "series.json")
        s = jload(p)
        s["plan"]["format_mix"] = ["comparison", "ranking"]
        jsave(p, s)
        code, o, e = self.t("episode", "new")
        self.assertEqual(code, 0, e)
        self.assertEqual(self.epj(2)["format"], "comparison")
        self.assertIn("format_mix 첫 번째", o)
        code, o, e = self.t("episode", "new", "--format", "quiz", "--pillar", "p2")
        self.assertEqual(code, 0, e)
        self.assertEqual(self.epj(3)["format"], "quiz")
        self.assertEqual(self.epj(3)["pillar"], "p2")
        self.assertIn("format_mix", o)  # 포맷 밖 경고
        self.assertIn("경고", o)

    def test_default_ranking_without_approved_plan(self):
        p = os.path.join(self.root, "series.json")
        s = jload(p)
        s["plan"]["approved"] = False
        s["plan"]["format_mix"] = ["comparison"]
        jsave(p, s)
        self.assertEqual(self.t("episode", "new")[0], 0)
        self.assertEqual(self.epj(2)["format"], "ranking")

    def test_unknown_pillar_rejected(self):
        code, o, e = self.t("episode", "new", "--pillar", "p9")
        self.assertEqual(code, 2)
        self.assertIn("p9", e)
        self.assertFalse(os.path.exists(os.path.join(self.root, "episodes/ep02")))

    def test_qa_pillar_warning(self):
        self.ingest_all()
        p = os.path.join(self.root, "episodes/ep01/episode.json")
        e = jload(p)
        del e["pillar"]
        jsave(p, e)
        code, o, err = self.t("qa", "1")
        self.assertIn("어느 콘텐츠 기둥인지 적으세요", o)
        e["pillar"] = "p1"
        jsave(p, e)
        self.assertNotIn("콘텐츠 기둥", self.t("qa", "1")[1])

    def test_qa_boundary_warning(self):
        self.ingest_all()
        sp = os.path.join(self.root, "series.json")
        s = jload(sp)
        s["plan"]["boundaries"] = ["경쟁사X, 정치"]
        jsave(sp, s)
        self.assertNotIn("다루지 않을 것", self.t("qa", "1")[1])
        bp = os.path.join(self.root, "episodes/ep01/storyboard.json")
        sb = jload(bp)
        sb["pages"][2]["lines"].append({"id": "zz", "kind": "speech", "speaker": "윤서", "text": "경쟁사X 가 더 싸던데"})
        jsave(bp, sb)
        o = self.t("qa", "1")[1]
        self.assertIn("'경쟁사X'", o)
        self.assertNotIn("'정치'", o)

    def test_status_pillar_distribution(self):
        for n, pillar in ((2, "p1"), (3, "p2"), (4, "p1")):
            self.t("episode", "new", "--pillar", pillar)
        o = self.t("status")[1]
        self.assertIn("기둥 분포: p1 3편 75%/목표 35%, p2 1편 25%/목표 30%, p3 0편 0%/목표 15%, p4 0편 0%/목표 20%", o)

    def test_example_episode_has_pillar(self):
        self.assertEqual(self.epj(1)["pillar"], "p1")
        for c in self.epj(1)["topic_candidates"]:
            self.assertIn(c["pillar"], ("p1", "p2", "p3", "p4"))


if __name__ == "__main__":
    unittest.main()
