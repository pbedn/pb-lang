# PB implementation of a linear congruential pseudorandom number generator (LCG)
# using only arithmetic, without bitwise operators or hexadecimal literals.

# Internal state (initialized to 1)
_state: int = 1

def seed(x: int) -> None:
    """Initialize the random number generator with an integer seed."""
    global _state
    _state = x % 4294967296  # simulate 32-bit unsigned wraparound

def _next() -> int:
    """Internal: generate next pseudo-random 32-bit integer."""
    global _state
    _state = (_state * 1664525 + 1013904223) % 4294967296
    return _state

def randint(a: int, b: int) -> int:
    """
    Return a random integer N such that a <= N <= b.
    """
    r: int = _next()
    return a + (r % (b - a + 1))

def random() -> float:
    """
    Return a float in [0.0, 1.0).
    """
    r: int = _next()
    return r / 4294967296.0

def uniform(a: float, b: float) -> float:
    """
    Return a float in [a, b].
    """
    return a + (b - a) * random()
