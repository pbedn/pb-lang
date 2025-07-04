import os
import tempfile

from pb_pipeline import compile_code_to_c_and_h
from module_loader import load_module
from main import collect_vendor_build_info, write_module_code_files


def create_binding_module(tmpdir):
    mod_dir = os.path.join(tmpdir, "vendor", "testlib")
    os.makedirs(mod_dir, exist_ok=True)
    pb_path = os.path.join(mod_dir, "testlib.pb")
    with open(pb_path, "w") as f:
        f.write("def add(x: int, y: int) -> int:\n    return 0\n")
    meta_path = os.path.join(mod_dir, "metadata.json")
    with open(meta_path, "w") as f:
        f.write('{"link_flags": ["-ltest"], "native": true}')
    return pb_path, mod_dir


def test_compile_binding_skips_codegen():
    with tempfile.TemporaryDirectory() as tmp:
        pb_path, _ = create_binding_module(tmp)
        with open(pb_path) as f:
            source = f.read()
        h, c, ast, mods = compile_code_to_c_and_h(source, module_name="testlib", pb_path=pb_path)
        assert h is None and c is None
        assert ast is not None
        assert mods == {}


def test_load_module_binding_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        pb_path, mod_dir = create_binding_module(tmp)
        loaded = {}
        mod = load_module(["testlib"], [mod_dir], loaded)
        assert mod.native_binding
        assert mod.vendor_metadata == {"link_flags": ["-ltest"], "native": True}
        inc, lib, flags = collect_vendor_build_info(loaded)
        assert "-ltest" in flags
        # write_module_code_files should return None
        assert write_module_code_files(mod, mod_dir) is None

