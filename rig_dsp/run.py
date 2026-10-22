"""
Progress reporting and pool sizing for the scripts in `tools/`.

Inside the source project these defer to its own `progress_telemetry.Progress`
and `pool_size.workers` (found through the `RIG_PROJECT_ROOT` environment
variable), so its status tooling sees runs launched from here. Anywhere else
they fall back to the small versions below.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta

_root = os.environ.get("RIG_PROJECT_ROOT")
if _root and _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from progress_telemetry import Progress  # type: ignore  # noqa: F401
except ImportError:
    class Progress:  # minimal stand-in: % done, ETA, timestamps
        def __init__(self, total, name, upper_bound=False, **_):
            self.total, self.name, self.done = max(total, 1), name, 0
            self.t0 = time.time()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            print(f"[{datetime.now():%H:%M:%S}] {self.name}: finished "
                  f"{self.done}/{self.total} in {timedelta(seconds=int(time.time() - self.t0))}",
                  flush=True)

        def step(self, n=1, note=""):
            self.done += n
            el = time.time() - self.t0
            eta = el / self.done * (self.total - self.done)
            print(f"[{datetime.now():%H:%M:%S}] {self.name}: {self.done}/{self.total} "
                  f"({100 * self.done / self.total:.0f}%) ETA {timedelta(seconds=int(eta))} {note}",
                  flush=True)

try:
    from pool_size import workers  # type: ignore  # noqa: F401
except ImportError:
    def workers(per_worker_gb, jobs=None, requested=None, name="", **_):
        if requested:
            return requested
        n = max(1, (os.cpu_count() or 2) - 1)
        return max(1, min(n, jobs or n))


def pin_blas():
    """One BLAS thread per worker: call in the parent before creating a pool."""
    for k in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ[k] = "1"
