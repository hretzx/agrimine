"""
core/cache.py
-------------
A tiny cache for the model trainers and the expensive tables, with NO Streamlit dependency.

    @cached
    def train_id3(): ...          # trained once per process, then served from memory

It replaces st.cache_data / st.cache_resource in the logic layer. One behaviour of st.cache_data is kept on purpose:
a pandas DataFrame is returned as a COPY, so a caller that adds a column cannot change what the next caller gets.
(Dicts, models and numpy arrays are shared, like st.cache_resource did; treat them as read-only.)
"""
import functools
import threading

import pandas as pd


def _safe(value):
    """DataFrames (also inside a tuple) are copied on the way out."""
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, tuple):
        return tuple(_safe(v) for v in value)
    return value


def cached(fn):
    """Remember the result per argument values (arguments must be hashable); DataFrames come back as copies; thread-safe."""
    memo = functools.lru_cache(maxsize=None)(fn)
    lock = threading.RLock()     # a second caller WAITS for a computation already running instead of repeating it

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with lock:
            return _safe(memo(*args, **kwargs))

    wrapper.cache_clear = memo.cache_clear
    wrapper.cache_info = memo.cache_info
    wrapper.__wrapped__ = fn
    return wrapper
