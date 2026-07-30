#!/usr/bin/env python3
"""
Tests for the bounded-concurrency helper.

The relevance stage made ~40 embedding calls and ~15 triage calls sequentially;
the latency was the stage. These must run concurrently without losing results,
dropping order, or letting one failure abort the batch.
"""

import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.parallel import map_bounded


class TestResults(unittest.TestCase):
    def test_results_in_input_order(self):
        outcomes = map_bounded(lambda n: n * 2, [1, 2, 3, 4, 5], workers=4)
        self.assertEqual([item for item, _ in outcomes], [1, 2, 3, 4, 5])
        self.assertEqual([result for _, result in outcomes], [2, 4, 6, 8, 10])

    def test_empty_input(self):
        self.assertEqual(map_bounded(lambda n: n, [], workers=4), [])

    def test_single_item_runs_inline(self):
        self.assertEqual(map_bounded(lambda n: n + 1, [1], workers=4), [(1, 2)])

    def test_one_worker_is_sequential(self):
        order = []
        map_bounded(lambda n: order.append(n), [1, 2, 3], workers=1)
        self.assertEqual(order, [1, 2, 3])


class TestFailureIsolation(unittest.TestCase):
    def test_failure_returned_not_raised(self):
        def maybe_fail(n):
            if n == 2:
                raise ValueError("boom")
            return n

        outcomes = map_bounded(maybe_fail, [1, 2, 3], workers=3)
        self.assertEqual(outcomes[0], (1, 1))
        self.assertIsInstance(outcomes[1][1], ValueError)
        self.assertEqual(outcomes[2], (3, 3))

    def test_all_failing_still_returns_every_item(self):
        outcomes = map_bounded(lambda n: 1 / 0, [1, 2], workers=2)
        self.assertEqual(len(outcomes), 2)
        self.assertTrue(all(isinstance(r, Exception) for _, r in outcomes))


class TestConcurrency(unittest.TestCase):
    def test_calls_actually_overlap(self):
        started = threading.Semaphore(0)
        peak = {"n": 0, "current": 0}
        lock = threading.Lock()

        def slow(_):
            with lock:
                peak["current"] += 1
                peak["n"] = max(peak["n"], peak["current"])
            time.sleep(0.05)
            with lock:
                peak["current"] -= 1
            started.release()
            return True

        map_bounded(slow, list(range(6)), workers=3)
        self.assertGreater(peak["n"], 1, "calls did not overlap")

    def test_worker_cap_respected(self):
        peak = {"n": 0, "current": 0}
        lock = threading.Lock()

        def slow(_):
            with lock:
                peak["current"] += 1
                peak["n"] = max(peak["n"], peak["current"])
            time.sleep(0.05)
            with lock:
                peak["current"] -= 1
            return True

        map_bounded(slow, list(range(12)), workers=3)
        self.assertLessEqual(peak["n"], 3, "exceeded the worker cap")

    def test_faster_than_sequential(self):
        def slow(_):
            time.sleep(0.05)
            return True

        start = time.monotonic()
        map_bounded(slow, list(range(8)), workers=8)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.30, f"took {elapsed:.2f}s; expected well under 0.4s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
