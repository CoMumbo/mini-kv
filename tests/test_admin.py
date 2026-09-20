import os
import tempfile
import pytest

from app.store import KVStore
from app.persistence import AOF
from app.admin import create_admin_app


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as tmp:
        aof = AOF(os.path.join(tmp, "test.aof"))
        store = KVStore()
        app = create_admin_app(store, aof)
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c, store
        aof.close()


def test_health(client):
    c, _ = client
    r = c.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert "uptime_seconds" in body


def test_stats_shape(client):
    c, store = client
    store.set("a", "1")
    store.set("b", "2")
    r = c.get("/stats")
    assert r.status_code == 200
    body = r.get_json()
    assert body["keys"] == 2
    assert "boots" in body
    assert "commands" in body
    assert body["aof_path"].endswith(".aof")