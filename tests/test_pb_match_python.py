import subprocess
import sys
import os
import unittest

from tests import root_dir


class TestRefLangOutputMatch(unittest.TestCase):

    def test_ref_lang_python_vs_pb_output(self):
        lang_path = os.path.join(root_dir, "ref", "lang.pb")
        run_pb_script = os.path.join(root_dir, "run_pb_as_python.py")
        pb_main = os.path.join(root_dir, "src", "main.py")

        # Run using Python (via injected main() call)
        py_result = subprocess.run(
            [sys.executable, run_pb_script, lang_path],
            capture_output=True,
            text=True,
            cwd=root_dir,
        )
        self.assertEqual(py_result.returncode, 0, f"Python run failed:\n{py_result.stderr}")
        output_python = py_result.stdout.strip().splitlines()

        # Run using PB toolchain
        pb_result = subprocess.run(
            [sys.executable, pb_main, "run", lang_path],
            capture_output=True,
            text=True,
            cwd=os.path.join(root_dir, "src"),
        )
        self.assertEqual(pb_result.returncode, 0, f"PB run failed:\n{pb_result.stderr}")
        output_pb = pb_result.stdout.strip().splitlines()

        self.assertEqual(output_python, output_pb, "PB and Python outputs differ")


if __name__ == "__main__":
    unittest.main()
