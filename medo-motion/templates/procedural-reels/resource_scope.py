"""Explicit scene resource scope; dispose all registered resources exactly once, in reverse order."""
from __future__ import annotations

import warnings


class ResourceScope:
    def __init__(self): self._stack = []; self.closed = False
    def defer(self, dispose):
        if self.closed or not callable(dispose): raise ValueError('scope closed or disposer invalid')
        self._stack.append(dispose)
    def close(self):
        if self.closed: return
        self.closed = True; errors = []
        while self._stack:
            try: self._stack.pop()()
            except Exception as error: errors.append(error)
        if errors: raise RuntimeError(f'{len(errors)} resource cleanup(s) failed') from errors[0]
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, traceback):
        try: self.close()
        except Exception as cleanup:
            if exc is None: raise
            warnings.warn(f'resource cleanup failed during another error: {cleanup}', RuntimeWarning, stacklevel=2)
        return False
