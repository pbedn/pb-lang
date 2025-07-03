import os, tempfile, unittest
from pb_pipeline import compile_code_to_c_and_h

class TestVendorInterop(unittest.TestCase):
    def test_vendor_header_included(self):
        with tempfile.TemporaryDirectory() as tempdir:
            vendor = os.path.join(tempdir, "vendor")
            os.makedirs(vendor)
            vendor_file = os.path.join(vendor, "raylib.pb")
            with open(vendor_file, "w") as f:
                f.write("# vendor module\n# headers: raylib.h\n")
                f.write("def InitWindow(width: int, height: int, title: str) -> None: ...\n")

            main_path = os.path.join(tempdir, "main.pb")
            with open(main_path, "w") as f:
                f.write("import raylib\n")
                f.write("def main() -> int:\n")
                f.write("    raylib.InitWindow(800, 600, \"Hi\")\n")
                f.write("    return 0\n")

            h, c, *_ = compile_code_to_c_and_h(open(main_path).read(), module_name="main", pb_path=main_path)
            self.assertIn('#include "raylib.h"', c)
            self.assertNotIn('void InitWindow', c)
            self.assertNotIn('InitWindow(', h)

if __name__ == '__main__':
    unittest.main()

