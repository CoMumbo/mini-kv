import os
import threading
import time
import logging

log = logging.getLogger("mini-kv.aof")


class AOF:
    """Append-only file: every write command is appended to disk.

    On startup, the file is read line by line and replayed to rebuild state.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._file = open(path, "a", encoding="utf-8", buffering=1)
        log.info("AOF opened at %s", path)

    def append(self, line: str) -> None:
        """Write one command line to disk and flush."""
        with self._lock:
            self._file.write(line.rstrip("\n") + "\n")
            self._file.flush()
            os.fsync(self._file.fileno())

    def replay(self) -> list[str]:
        """Return every logged line, in order. Called once at startup."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") for line in f if line.strip()]

    def rewrite(self, lines: list[str]) -> None:
        """Replace the file with a compacted set of lines (used by compaction)."""
        with self._lock:
            self._file.close()
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line.rstrip("\n") + "\n")
            os.replace(tmp, self.path)
            self._file = open(self.path, "a", encoding="utf-8", buffering=1)
            log.info("AOF rewritten with %d lines", len(lines))

    def compact(self, live_state: dict[str, str], expires: dict[str, float]) -> int:
        """Rewrite the AOF to its minimal form.

        `live_state` is the current key/value dict; `expires` maps keys to
        their absolute unix expiration timestamps.

        Returns the number of lines written.
        """
        lines: list[str] = []
        for key, value in live_state.items():
            lines.append(f"SET {key} {value}")
        now = time.time()
        for key, expiry in expires.items():
            if key in live_state:
                remaining = int(expiry - now)
                if remaining > 0:
                    lines.append(f"EXPIRE {key} {remaining}")
        self.rewrite(lines)
        return len(lines)

    def close(self) -> None:
        with self._lock:
            self._file.close()