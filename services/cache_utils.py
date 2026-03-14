"""
Simple in-memory TTL cache to replace @st.cache_data.

@st.cache_data on Streamlit Cloud attempts to pickle/serialize return values
and raises UnboundLocalError when serialization fails on complex Supabase
response objects. This module provides a drop-in replacement that stores
results in a plain dict with timestamps — no serialization required.
"""
import time
import functools
import logging

logger = logging.getLogger("sylemax.cache_utils")

# Global in-process cache store: {cache_key: (timestamp, value)}
_CACHE: dict = {}


def ttl_cache(ttl: int = 60):
    """
    Decorator factory. Usage:

        @ttl_cache(ttl=60)
        def my_func(arg1, arg2):
            ...

    Cache key is built from (function qualified name, args, sorted kwargs).
    TTL is in seconds. Passing ttl=0 disables caching.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if ttl == 0:
                return func(*args, **kwargs)
            try:
                key = (func.__qualname__, args, tuple(sorted(kwargs.items())))
            except TypeError:
                # Unhashable args — skip cache
                return func(*args, **kwargs)

            now = time.monotonic()
            if key in _CACHE:
                ts, val = _CACHE[key]
                if now - ts < ttl:
                    return val

            result = func(*args, **kwargs)
            _CACHE[key] = (now, result)
            return result

        def clear():
            """Remove all entries for this function from the cache."""
            prefix = func.__qualname__
            stale = [k for k in _CACHE if k[0] == prefix]
            for k in stale:
                del _CACHE[k]

        wrapper.clear = clear
        return wrapper
    return decorator


def clear_all():
    """Clear the entire in-process cache (replaces st.cache_data.clear())."""
    _CACHE.clear()
    logger.debug("Full cache cleared.")
