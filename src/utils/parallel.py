#!/usr/bin/env python3
"""
Bounded concurrency helper.

The relevance stage makes ~40 embedding calls and ~15 triage calls, and the
extraction stage downloads a PDF per paper. Run sequentially these are minutes of
round-trip latency. They are independent, so a small pool removes most of it.

Bounded, not unbounded: a local Ollama serving a 32B model degrades sharply if
flooded, and arXiv should not be hammered.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, List, Tuple


def map_bounded(fn: Callable, items: Iterable, workers: int = 4,
                label: str = "") -> List[Tuple[object, object]]:
    """
    Apply `fn` to each item using at most `workers` threads.

    Results come back in input order. An item whose call raises yields its
    exception rather than losing the whole batch - callers decide what a failure
    means.

    Returns:
        [(item, result_or_exception), ...] in input order
    """
    items = list(items)
    if not items:
        return []
    if workers <= 1 or len(items) == 1:
        return [(item, _call(fn, item)) for item in items]

    with ThreadPoolExecutor(max_workers=min(workers, len(items)),
                            thread_name_prefix=label or "torri") as pool:
        return list(zip(items, pool.map(lambda item: _call(fn, item), items)))


def _call(fn: Callable, item):
    try:
        return fn(item)
    except Exception as exc:  # returned, not raised: one failure must not abort
        return exc
