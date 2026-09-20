import threading
import time
import logging

log = logging.getLogger("mini-kv.ttl")


class TTLSweeper:
    """Background thread that removes expired keys proactively.

    Without this, expired keys linger in memory until someone happens
    to read them. This sweeper guarantees they're cleaned up on a schedule,
    regardless of access patterns.
    """

    def __init__(self, store, interval: float = 1.0):
        self.store = store
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="ttl-sweeper", daemon=True)
        self._thread.start()
        log.info("TTL sweeper started (interval=%.1fs)", self.interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            log.info("TTL sweeper stopped")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                removed = self.store.sweep_expired()
                if removed:
                    log.info("swept %d expired key(s)", removed)
            except Exception:
                log.exception("TTL sweeper error")
            self._stop.wait(self.interval)