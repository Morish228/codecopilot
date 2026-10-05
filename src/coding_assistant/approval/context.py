from contextlib import contextmanager
from contextvars import ContextVar

_approval_bypass: ContextVar[bool] = ContextVar("approval_bypass", default=False)


def approval_bypass_active() -> bool:
    return _approval_bypass.get()


@contextmanager
def with_approval_bypass():
    token = _approval_bypass.set(True)
    try:
        yield
    finally:
        _approval_bypass.reset(token)
