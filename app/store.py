import threading
import time
from typing import Optional


class KVStore:
    def __init__(self):
        self._data: dict[str, str] = {}
        self._expires: dict[str, float] = {}
        self._lock = threading.RLock()

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._data[key] = value
            self._expires.pop(key, None)

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            self._maybe_expire(key)
            return self._data.get(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            self._expires.pop(key, None)
            return self._data.pop(key, None) is not None

    def expire(self, key: str, seconds: int) -> bool:
        with self._lock:
            if key not in self._data:
                return False
            self._expires[key] = time.time() + seconds
            return True

    def ttl(self, key: str) -> int:
        with self._lock:
            if key not in self._data:
                return -2
            if key not in self._expires:
                return -1
            remaining = int(self._expires[key] - time.time())
            return max(remaining, -2)

    def keys(self) -> list[str]:
        with self._lock:
            for k in list(self._expires):
                self._maybe_expire(k)
            return list(self._data.keys())

    def flush(self) -> None:
        with self._lock:
            self._data.clear()
            self._expires.clear()

    def _maybe_expire(self, key: str) -> None:
        exp = self._expires.get(key)
        if exp is not None and exp <= time.time():
            self._expires.pop(key, None)
            self._data.pop(key, None)

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            for k in list(self._expires):
                self._maybe_expire(k)
            return dict(self._data)