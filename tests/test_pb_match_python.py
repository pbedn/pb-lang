import subprocess
import sys
import os
import unittest

from tests import root_dir

examples_dir = os.path.join(root_dir, "examples")


class RuntimeHelper(unittest.TestCase):

    def _run_python(self, path):
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            cwd=root_dir,
        )
        self.assertEqual(result.returncode, 0, f"Python run failed for {path}:\n{result.stderr}")
        return result.stdout.strip().splitlines()

    def _run_pb(self, path):
        pb_main = os.path.join(root_dir, "src", "main.py")
        result = subprocess.run(
            [sys.executable, pb_main, "run", path],
            capture_output=True,
            text=True,
            cwd=os.path.join(root_dir, "src"),
        )
        self.assertEqual(result.returncode, 0, f"PB run failed for {path}:\n{result.stderr}")
        return result.stdout.strip().splitlines()


class TestRefLangOutputMatch(RuntimeHelper):

    def test_ref_lang_python_vs_pb_output(self):
        lang_path = os.path.join(root_dir, "ref", "lang.pb")
        out_py = self._run_python(lang_path)
        out_pb = self._run_pb(lang_path)
        self.assertEqual(out_py, out_pb)


class TestExamplesPythonVsPb(RuntimeHelper):

    def test_adv_fstrings(self):
        path = os.path.join(examples_dir, "adv_fstrings.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    def test_arr_rw(self):
        path = os.path.join(examples_dir, "arr_rw.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    def test_builtins(self):
        path = os.path.join(examples_dir, "builtins.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    def test_classes(self):
        path = os.path.join(examples_dir, "classes.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    def test_default_args(self):
        path = os.path.join(examples_dir, "default_args.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    # def test_exception(self):
    #     path = os.path.join(examples_dir, "exception.pb")
    #     with self.subTest(example="exception.pb"):
    #         out_py = self._run_python(path)
    #         out_pb = self._run_pb(path)
    #         self.assertEqual(out_py, out_pb)

    # def test_exceptions2(self):
    #     path = os.path.join(examples_dir, "exceptions2.pb")
    #     with self.subTest(example="exception.pb"):
    #         out_py = self._run_python(path)
    #         out_pb = self._run_pb(path)
    #         self.assertEqual(out_py, out_pb)

    def test_functions(self):
        path = os.path.join(examples_dir, "functions.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    def test_hello(self):
        path = os.path.join(examples_dir, "hello.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    def test_list_indexing(self):
        path = os.path.join(examples_dir, "list_indexing.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    def test_test(self):
        path = os.path.join(examples_dir, "test.pb")
        out_py = self._run_python(path)
        out_pb = self._run_pb(path)
        self.assertEqual(out_py, out_pb)

    # def test_list_indexing_python_vs_pb_output(self):
    #     pb_path = os.path.join(root_dir, "examples", "list_indexing.pb")
    #     run_pb_script = os.path.join(root_dir, "run_pb_as_python.py")
    #     pb_main = os.path.join(root_dir, "src", "main.py")

    #     py_result = subprocess.run(
    #         [sys.executable, run_pb_script, pb_path],
    #         capture_output=True,
    #         text=True,
    #         cwd=root_dir,
    #     )
    #     self.assertEqual(py_result.returncode, 0, f"Python run failed:\n{py_result.stderr}")
    #     output_python = py_result.stdout.strip().splitlines()

    #     pb_result = subprocess.run(
    #         [sys.executable, pb_main, "run", pb_path],
    #         capture_output=True,
    #         text=True,
    #         cwd=os.path.join(root_dir, "src"),
    #     )
    #     self.assertEqual(pb_result.returncode, 0, f"PB run failed:\n{pb_result.stderr}")
    #     output_pb = pb_result.stdout.strip().splitlines()

    #     self.assertEqual(output_python, output_pb, "PB and Python outputs differ")


if __name__ == "__main__":
    unittest.main()
