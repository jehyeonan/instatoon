import os
import subprocess
import sys
import unittest

import helpers

TOON = os.path.join(helpers.SKILL, "scripts", "toon")


class ConcurrencyTests(unittest.TestCase):
    def test_parallel_style_ingest_gets_distinct_versions(self):
        d, root = helpers.temp_series()
        imgs = [helpers.make_image(os.path.join(d, "s%d.png" % i)) for i in range(4)]
        env = dict(os.environ, PYTHONPATH=helpers.SKILL)
        procs = [subprocess.Popen([sys.executable, "-m", "toonkit.cli", "--root", root, "style", "ingest", p],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) for p in imgs]
        for p in procs:
            p.communicate()
            self.assertEqual(p.returncode, 0)
        files = sorted(f for f in os.listdir(os.path.join(root, "style")) if f.startswith("sample_v"))
        self.assertEqual(len(files), 4, files)
        code, o, e = helpers.toon("--root", root, "status")
        self.assertIn("샘플 4", o.replace("샘플 4개", "샘플 4"))


if __name__ == "__main__":
    unittest.main()
