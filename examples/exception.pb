class Exception:
    def __init__(self, msg: str):
        self.msg = msg

class RuntimeError(Exception):
    pass

def crash():
    raise RuntimeError("division by zero")

def main():
    crash()
