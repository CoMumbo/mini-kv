import time
from app.store import KVStore


def test_set_get():
    s = KVStore()
    s.set("a", "1")
    assert s.get("a") == "1"


def test_delete():
    s = KVStore()
    s.set("a", "1")
    assert s.delete("a") is True
    assert s.get("a") is None
    assert s.delete("a") is False


def test_expire_and_ttl():
    s = KVStore()
    s.set("a", "1")
    assert s.ttl("a") == -1
    s.expire("a", 5)
    assert 0 <= s.ttl("a") <= 5


def test_expired_key_is_gone():
    s = KVStore()
    s.set("a", "1")
    s.expire("a", 1)
    time.sleep(1.1)
    assert s.get("a") is None


def test_keys_and_flush():
    s = KVStore()
    s.set("a", "1")
    s.set("b", "2")
    assert set(s.keys()) == {"a", "b"}
    s.flush()
    assert s.keys() == []


def test_sweep_expired_removes_multiple():
    s = KVStore()
    s.set("a", "1")
    s.set("b", "2")
    s.set("c", "3")
    s.expire("a", 1)
    s.expire("b", 1)
    time.sleep(1.1)
    removed = s.sweep_expired()
    assert removed == 2
    assert s.keys() == ["c"]


def test_sweep_expired_no_expired_keys():
    s = KVStore()
    s.set("a", "1")
    s.set("b", "2")
    removed = s.sweep_expired()
    assert removed == 0
    assert set(s.keys()) == {"a", "b"}