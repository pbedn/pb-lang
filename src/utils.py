import time
from functools import wraps

@wraps
def elapsed(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[info] Elapsed time for {func.__name__}: {elapsed*1000:.2f} ms")
        return func
    return wrapper
