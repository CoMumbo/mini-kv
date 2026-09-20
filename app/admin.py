import time
import logging
from flask import Flask, jsonify
from app.config import Config
from app.db import init_db, get_stats

log = logging.getLogger("mini-kv.admin")

_START_TIME = time.time()


def create_admin_app(store, aof) -> Flask:
    """Build the Flask admin app. `store` and `aof` are injected by the server."""

    app = Flask("mini-kv-admin")

    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "uptime_seconds": round(time.time() - _START_TIME, 1),
        })

    @app.route("/stats")
    def stats():
        db_stats = get_stats()
        return jsonify({
            "uptime_seconds": round(time.time() - _START_TIME, 1),
            "keys": len(store.keys()),
            "boots": db_stats["boots"],
            "commands": db_stats["commands"],
            "aof_path": aof.path,
        })

    return app