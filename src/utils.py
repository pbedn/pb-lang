import time
from functools import wraps

def elapsed(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start
        print(f"[info] Elapsed time for {func.__name__}: {elapsed_time*1000:.2f} ms")
        return result
    return wrapper
