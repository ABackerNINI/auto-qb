> 版本: 3.32.6 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### Acquire lock with timeout

Source: https://github.com/tox-dev/filelock/blob/main/_autodocs/api-reference/base-file-lock.md

Recommended usage for acquiring a lock with a timeout. Creates a FileLock with a 1-second timeout and uses the context manager to enter the exclusive section. The lock is automatically released when the block exits.

```python
lock = FileLock("state.lock", timeout=1)
with lock.acquire():
    # exclusive section
```

--------------------------------

### acquire

Source: https://github.com/tox-dev/filelock/blob/main/_autodocs/api-reference/base-file-lock.md

Acquires the file lock with configurable timeout, polling interval, blocking behavior, and cancellation. Returns a context-aware proxy that releases the lock on exit.

```APIDOC
## acquire(timeout=None, poll_interval=None, *, poll_intervall=None, blocking=None, cancel_check=None)

### Description
Acquires the file lock, blocking or non-blocking, with configurable timeout, polling interval, and cancellation. Returns a context-aware proxy that releases the lock on exit.

### Method
acquire

### Parameters
#### Parameters
- **timeout** (`float | None`) - Optional - maximum wait in seconds; `None` → use `self.timeout`; `< 0` → block forever; `0` → one attempt
- **poll_interval** (`float | None`) - Optional - poll cadence; `None` → use `self.poll_interval`
- **poll_intervall** (`float | None`) - Optional - deprecated alias kept for backwards compatibility; emits `DeprecationWarning` (`"use poll_interval instead of poll_intervall"`)
- **blocking** (`bool | None`) - Optional - `False` returns (raising) after the first failed attempt; `None` → use `self.blocking`
- **cancel_check** (`Callable[[], bool] | None`) - Optional - called each poll iteration; when it returns `True`, acquisition raises `Timeout` like an expired timeout

### Returns
`AcquireReturnProxy` — a context-aware object whose `__enter__` returns the lock and whose `__exit__` releases it (with `context_error_policy` reconciliation). Reentrancy: each successful `acquire` increments `lock_counter`; `release` decrements it and fully releases only at 0.

### Throws
- `Timeout` if the lock is not acquired within the timeout, if `blocking=False` on first contention, or if `cancel_check()` returns `True`
- `RuntimeError` if the instance was inherited across `fork()` ("was inherited across fork; construct a new instance")
- `RuntimeError` if a *different* live instance already holds the path in the same deadlock scope ("Deadlock: lock ... is already held by a different FileLock instance in this thread" — only for the first, indefinitely-blocking acquire; use `is_singleton=True` for cross-instance reentrancy)

### Example
```python
lock = FileLock("state.lock", timeout=1)
with lock.acquire():
    # exclusive section
```

### Example
```python
import threading
from filelock import FileLock, Timeout

cancelled = threading.Event()
lock = FileLock("state.lock")
try:
    with lock.acquire(timeout=2, cancel_check=cancelled.is_set, poll_interval=0.05):
        pass
except Timeout as exc:
    print(f"gave up on {exc.lock_file}")
```
```

--------------------------------

### Acquire and release a FileLock with a context manager

Source: https://github.com/tox-dev/filelock/blob/main/docs/tutorials.rst

Uses the lock with a with statement. Inside the block the lock is held; outside it is released. Only one process prints at a time when run in multiple terminals.

```python
with lock:
    # Inside this block, we hold the lock
    print("I have the lock!")
# Outside this block, the lock is released
```

--------------------------------

### Wait for a lock with a timeout

Source: https://github.com/tox-dev/filelock/blob/main/docs/how-to.rst

Use the context manager form to wait for a lock with a timeout. The first block shows the default timeout of 10 seconds; the second passes timeout=5 to acquire(). Both raise Timeout if the lock is not acquired within the limit.

```python
try:
    with lock:
        # This will wait up to 10 seconds for the lock
        print("Got the lock!")
except Timeout:
    print("Couldn't get the lock after 10 seconds")
```

```python
lock = FileLock("work.lock")

try:
    with lock.acquire(timeout=5):
        print("Got the lock!")
except Timeout:
    print("Timeout after 5 seconds")
```

### How-to guides > Handle lock timeouts

Source: https://github.com/tox-dev/filelock/blob/main/docs/how-to.rst

When another process holds a lock, you might want to give up after a certain time rather than waiting forever.

Use the ``timeout`` parameter when acquiring a lock:

.. code-block:: python

    from filelock import FileLock, Timeout

    lock = FileLock("work.lock", timeout=10)