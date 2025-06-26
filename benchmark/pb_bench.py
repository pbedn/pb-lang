import subprocess
import time
import os
import sys
import psutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from main import build, get_build_output_path

BENCHMARKS = [
    ("fib", "Calculates and prints the 38th Fibonacci number"),
    ("arith", "Calculates and prints a sum for numbers up to 50 million."),
]

PB_CMD = r"python run.py run benchmark\\{name}.pb"
PY_CMD = r"python benchmark\\{name}.pb"


def run_pb_via_codegen_and_exec(pb_path: str, output_name: str) -> tuple[float, float, str]:
    """
    Compile PB file to C, link it with runtime, and measure execution.
    Returns: (time_taken, peak_memory_MB, output)
    """
    # Load PB source
    with open(pb_path, encoding="utf-8") as f:
        source = f.read()

    success = build(source, pb_path, output_name, verbose=False, debug=False)
    if not success:
        raise RuntimeError(f"PB-to-C build failed for: {pb_path}")

    exe_path = get_build_output_path(output_name + ".exe")
    return measure(exe_path)


def measure(cmd):
    """Run command and return (time_taken, peak_memory_MB, output)"""
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        p = psutil.Process(proc.pid)
        mem_peak = 0
        start = time.perf_counter()

        while proc.poll() is None:
            try:
                mem = p.memory_info().rss
                mem_peak = max(mem_peak, mem)
            except psutil.NoSuchProcess:
                break
            time.sleep(0.01)

        end = time.perf_counter()
        output = proc.stdout.read().decode().strip()
        return end - start, mem_peak / (1024 * 1024), output
    except Exception as e:
        return -1, -1, f"Error: {e}"

def clean_build_dir():
    subprocess.run("rm .\\build\\*.exe")

def run_all(repeats):
    print("PB Benchmark Results:")
    print()
    for name, info in BENCHMARKS:
        print(f"== {name.upper()} Average running time | Repeats={repeats} times ==")
        print(f"-- {info}")

        pb_times, c_times, py_times = [], [], []
        pb_out = c_out = py_out = None

        for _ in range(repeats):
            # print(f"{'PB_OUT':>15} {'C_OUT':>15} {'PY_OUT':>15} | {'PB_TIME':>8} {'C_TIME':>8} {'PY_TIME':>8}")

            pb_time, pb_mem, pb_out = measure(PB_CMD.format(name=name))
            
            c_time, c_mem, c_out = run_pb_via_codegen_and_exec(
                pb_path=os.path.join("benchmark", f"{name}.pb"),
                output_name=f"{name}_gen"
            )

            py_time, py_mem, py_out = measure(PY_CMD.format(name=name))

            # print(f"{pb_out:>15} {c_out:>15} {py_out:>15} | {pb_time:8.2f} {c_time:8.2f} {py_time:8.2f}")

            assert pb_out == c_out == py_out

            pb_times.append(pb_time)
            c_times.append(c_time)
            py_times.append(py_time)

            clean_build_dir()

        # Display averages
        def avg(values): return sum(values) / len(values)

        print()
        print("AVERAGE:")
        print(f"{'Lang':<5} {'Time (s)':<10} {'Output'}")
        print(f"{'PB':<5} {avg(pb_times):<10.3f} {pb_out}")
        print(f"{'C':<5} {avg(c_times):<10.3f} {c_out}")
        print(f"{'PY':<5} {avg(py_times):<10.3f} {py_out}")
        print()

if __name__ == "__main__":
    repeats = 5
    if len(sys.argv) > 1 and int(sys.argv[1]):
        repeats = int(sys.argv[1])

    os.makedirs("build", exist_ok=True)
    run_all(repeats)
