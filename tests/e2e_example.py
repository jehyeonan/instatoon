"""생성 없이 하는 예제 E2E: examples/yunseo 데이터로 prompt → ingest → grid → letter → qa → approve → export 를 돌린다.
그림은 INSTATOON_SAMPLE_DIR(p01.png~p08.png, sheet.png 가 있는 폴더)이 있으면 그것을, 없으면 회색 대체 이미지를 쓴다.
사용: python tests/e2e_example.py [출력폴더]   (기본 /tmp/instatoon_e2e)"""
import os
import shutil
import sys
import tempfile

import helpers

SRC = os.environ.get("INSTATOON_SAMPLE_DIR", "")


def run(*a):
    code, o, e = helpers.toon(*a)
    print("$ toon", " ".join(a[2:] if a and a[0] == "--root" else a), "->", code)
    if o.strip():
        print(o.rstrip()[:1500])
    if e.strip():
        print(e.rstrip())
    return code


def image(work, name):
    if SRC and os.path.exists(os.path.join(SRC, name)):
        return os.path.join(SRC, name)
    return helpers.make_image(os.path.join(work, name))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/instatoon_e2e"
    work = tempfile.mkdtemp(prefix="toon_e2e_")
    root = os.path.join(work, "series")
    shutil.copytree(helpers.EXAMPLE, root, ignore=shutil.ignore_patterns("*.jpg"))
    r = ["--root", root]
    assert run(*(r + ["character", "add", "tmp_blocked"])) == 2  # 승인된 그림체 샘플이 없으면 거부
    assert run(*(r + ["style", "ingest", image(work, "style_sample.png")])) == 0
    assert run(*(r + ["style", "approve"])) == 0
    assert run(*(r + ["character", "prompt", "yunseo"])) == 0
    assert run(*(r + ["character", "ingest", "yunseo", image(work, "sheet.png")])) == 0
    assert run(*(r + ["character", "approve", "yunseo"])) == 0
    assert run(*(r + ["prompt", "1"])) == 0
    for n in range(1, 9):
        assert run(*(r + ["ingest", "1", str(n), image(work, "p%02d.png" % n)])) == 0
    run(*(r + ["grid", "1", "2"]))
    assert run(*(r + ["letter", "1"])) == 0
    assert run(*(r + ["qa", "1"])) == 0
    for n in range(1, 9):
        assert run(*(r + ["approve", "1", str(n)])) == 0
    assert run(*(r + ["export", "1"])) == 0
    run(*(r + ["status", "1"]))
    os.makedirs(out, exist_ok=True)
    for n in (1, 3, 8):
        shutil.copyfile(os.path.join(root, "episodes/ep01/pages/p%02d/lettered.png" % n), os.path.join(out, "lettered_p%02d.png" % n))
    shutil.copyfile(os.path.join(root, "episodes/ep01/out/preview.jpg"), os.path.join(out, "preview.jpg"))
    print("결과:", out)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
