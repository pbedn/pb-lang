"""Compare executable PB, handwritten C, and Python; compilation is untimed."""
import argparse
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from main import build, get_build_output_path


def measure(command):
    start = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return time.perf_counter() - start, result.stdout.strip()


def run_benchmark(name, repeats, optimization, quick=False):
    with tempfile.TemporaryDirectory(prefix="pb-benchmark-") as directory:
        directory = Path(directory)
        pb_source = (ROOT / "benchmark" / f"{name}.pb").read_text()
        c_source = (ROOT / "benchmark" / f"{name}.c").read_text()
        if quick:
            pb_source = pb_source.replace("fib(38)", "fib(20)").replace("50_000_000", "50_000")
            c_source = c_source.replace("fib(38)", "fib(20)").replace("50000000", "50000")
        pb_path, c_path = directory / f"{name}.pb", directory / f"{name}.c"
        pb_path.write_text(pb_source)
        c_path.write_text(c_source)
        # Use a unique output name to avoid touching unrelated user builds.
        output = f"benchmark_{directory.name.replace('-', '_')}_{name}"
        success, _ = build(pb_source, str(pb_path), output, compile_flags=[optimization])
        if not success:
            raise RuntimeError(f"PB compilation failed: {name}")
        extension = ".exe" if os.name == "nt" else ""
        pb_exe = Path(get_build_output_path(output + extension))
        c_exe = directory / (name + extension)
        subprocess.run(["gcc", "-std=c99", optimization, str(c_path), "-o", str(c_exe)], check=True)
        commands = {"PB": [str(pb_exe)], "C": [str(c_exe)], "Python": [sys.executable, str(pb_path)]}
        timings = {language: [] for language in commands}
        expected = None
        try:
            # Verify and warm each implementation before measuring it.
            for language, command in commands.items():
                _, output_text = measure(command)
                if expected is None:
                    expected = output_text
                if output_text != expected:
                    raise RuntimeError(f"Output mismatch for {name}: {language}")
            for _ in range(repeats):
                for language, command in commands.items():
                    elapsed, output_text = measure(command)
                    if output_text != expected:
                        raise RuntimeError(f"Output changed for {name}: {language}")
                    timings[language].append(elapsed)
        finally:
            for suffix in (extension, ".c", ".h"):
                Path(get_build_output_path(output + suffix)).unlink(missing_ok=True)
        print(f"{name}: output={expected}; optimization={optimization}; repeats={repeats}")
        for language, values in timings.items():
            print(f"  {language:6} median={statistics.median(values):.6f}s")
        return timings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--optimization", choices=["-O0", "-O1", "-O2", "-O3"], default="-O2")
    parser.add_argument("--quick", action="store_true", help="Use small workloads for validation")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    for name in ("fib", "arith"):
        run_benchmark(name, args.repeats, args.optimization, args.quick)


if __name__ == "__main__":
    main()
