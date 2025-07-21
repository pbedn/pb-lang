import os
import tempfile
import json

from module_loader import load_module
from main import collect_vendor_build_info


def create_module(tmpdir):
    mod_dir = os.path.join(tmpdir, "vendor", "absmod")
    os.makedirs(mod_dir, exist_ok=True)
    pb_path = os.path.join(mod_dir, "absmod.pb")
    with open(pb_path, "w") as f:
        f.write("def f() -> int:\n    return 0\n")
    metadata = {
        "include_dirs": ["include"],
        "lib_dirs": ["lib"],
        "native": True
    }
    with open(os.path.join(mod_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f)
    os.makedirs(os.path.join(mod_dir, "include"), exist_ok=True)
    os.makedirs(os.path.join(mod_dir, "lib"), exist_ok=True)
    return mod_dir


def test_collect_vendor_build_info_returns_absolute_paths():
    with tempfile.TemporaryDirectory() as tmp:
        mod_dir = create_module(tmp)
        loaded = {}
        load_module(["absmod"], [mod_dir], loaded)
        inc_dirs, lib_dirs, _ = collect_vendor_build_info(loaded)
        inc_path = os.path.join(mod_dir, "include")
        lib_path = os.path.join(mod_dir, "lib")
        assert inc_path in inc_dirs
        assert lib_path in lib_dirs
        for p in inc_dirs | lib_dirs:
            assert os.path.isabs(p)
