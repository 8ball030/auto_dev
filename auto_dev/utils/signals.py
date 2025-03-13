"""Signal management utilities."""

import signal
from types import FrameType
from contextlib import contextmanager
from collections.abc import Callable


CallableSignalHandler = Callable[[int, FrameType], None]
SignalHandler = signal.Handlers | CallableSignalHandler


@contextmanager
def block(*signals: int):
    """Context manager to globally block specified signals by replacing their handlers with signal.SIG_IGN."""
    original_handlers = {sig: signal.getsignal(sig) for sig in signals}
    try:
        for sig in signals:
            signal.signal(sig, signal.SIG_IGN)
        yield
    finally:
        for sig, handler in original_handlers.items():
            signal.signal(sig, handler)


@contextmanager
def mask(*signals: int):
    """Context manager to temporarily block specified signals for the current thread by modifying its signal mask."""
    original_mask = signal.pthread_sigmask(signal.SIG_BLOCK, signals)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, original_mask)


@contextmanager
def replace_handler(signal_handler: SignalHandler, *signals: int):
    """Context manager to replace the signal handlers for specified signals with a custom handler."""
    original_handlers = {sig: signal.getsignal(sig) for sig in signals}
    try:
        for sig in signals:
            signal.signal(sig, signal_handler)
        yield
    finally:
        for sig, handler in original_handlers.items():
            signal.signal(sig, handler)
