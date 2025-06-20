import unittest
import tempfile
import os

from module_loader import resolve_module, load_module, ModuleNotFoundError

class TestModuleLoader(unittest.TestCase):
    def test_module_not_found(self):
        # Expected: ModuleNotFoundError is raised if file does not exist
        with self.assertRaises(ModuleNotFoundError):
            resolve_module(['this_module_should_not_exist'])

    def test_module_found_in_current_directory(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # Create foo.pb in the temporary directory
            file_path = os.path.join(tempdir, "foo.pb")
            with open(file_path, "w") as f:
                f.write("# test module\n")

            # Should resolve to foo.pb
            result = resolve_module(['foo'], search_paths=[tempdir])
            self.assertTrue(os.path.isfile(result))
            self.assertTrue(result.endswith("foo.pb"))

    def test_module_found_nested(self):
        with tempfile.TemporaryDirectory() as tempdir:
            # Create nested directory foo/bar.pb
            nested_dir = os.path.join(tempdir, "foo")
            os.makedirs(nested_dir)
            file_path = os.path.join(nested_dir, "bar.pb")
            with open(file_path, "w") as f:
                f.write("# nested module\n")

            # Should resolve to foo/bar.pb
            result = resolve_module(['foo', 'bar'], search_paths=[tempdir])
            self.assertTrue(os.path.isfile(result))
            self.assertTrue(result.endswith(os.path.join("foo", "bar.pb")))

    def test_module_not_found_message(self):
        try:
            resolve_module(['not_there'])
        except ModuleNotFoundError as e:
            # Expected: The error message should mention the module name and at least one path attempted
            self.assertIn("not_there", str(e))
            self.assertIn(".pb", str(e))
        else:
            self.fail("ModuleNotFoundError was not raised")

    def test_load_module_registers_exports(self):
        # Setup: Create a temporary .pb file for the module
        with tempfile.TemporaryDirectory() as tempdir:
            foo_path = os.path.join(tempdir, "foo.pb")
            with open(foo_path, "w") as f:
                f.write("def f():\n    pass\n")

            loaded_modules = {}
            mod = load_module(["foo"], [tempdir], loaded_modules)

            self.assertIn("f", mod.exports)
            self.assertEqual(mod.exports["f"], "function")
            self.assertIn(tuple(["foo"]), loaded_modules)

    def test_load_module_alias_registration(self):
        # Setup: Create a temporary .pb file for the module
        with tempfile.TemporaryDirectory() as tempdir:
            foo_path = os.path.join(tempdir, "foo.pb")
            with open(foo_path, "w") as f:
                f.write("def f():\n    pass\n")

            loaded_modules = {}
            mod = load_module(["foo"], [tempdir], loaded_modules)

            # Simulate orchestrator registering under an alias
            modules = {}
            modules["bar"] = mod
            self.assertIn("bar", modules)
            self.assertIn("f", modules["bar"].exports)


if __name__ == "__main__":
    unittest.main()
