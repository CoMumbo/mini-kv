import os
import tempfile
from app.persistence import AOF
from app.store import KVStore


def test_append_and_replay():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.aof")
        aof = AOF(path)

        aof.append("SET a 1")
        aof.append("SET b 2")
        aof.close()

        aof2 = AOF(path)
        lines = aof2.replay()
        aof2.close()

        assert lines == ["SET a 1", "SET b 2"]


def test_replay_empty_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "empty.aof")
        aof = AOF(path)
        lines = aof.replay()
        aof.close()
        assert lines == []


def test_rewrite_replaces_contents():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "rw.aof")
        aof = AOF(path)
        aof.append("SET a 1")
        aof.append("SET b 2")
        aof.rewrite(["SET a 1"])
        lines = aof.replay()
        aof.close()
        assert lines == ["SET a 1"]


def test_crash_recovery_simulation():
    """Simulate: writes hit disk, process restarts, state rebuilds."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "crash.aof")

        # Session 1: write commands to the log and apply them to a store
        store1 = KVStore()
        aof = AOF(path)
        for line in ["SET name alice", "SET city nairobi"]:
            aof.append(line)
            _, rest = line.split(maxsplit=1)
            k, v = rest.split()
            store1.set(k, v)
        aof.close()

        # Session 2: fresh store, replay the log
        store2 = KVStore()
        aof2 = AOF(path)
        for line in aof2.replay():
            cmd, rest = line.split(maxsplit=1)
            if cmd == "SET":
                k, v = rest.split()
                store2.set(k, v)
        aof2.close()

        assert store2.get("name") == "alice"
        assert store2.get("city") == "nairobi"