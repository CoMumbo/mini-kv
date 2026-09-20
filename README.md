# mini-kv

A small Redis-like key-value store written in Python, with a TCP protocol,
thread-safe in-memory storage, TTL support, **AOF persistence with crash
recovery**, **background TTL sweeping and log compaction**, and a **Flask
admin HTTP sidecar with SQLite-backed stats**.

## Status

✅ Core server working
✅ AOF persistence + replay-on-startup crash recovery
✅ TTL sweeper thread + AOF compaction
✅ Flask admin endpoints (`/health`, `/stats`) + SQLite metadata
🚧 Dockerization, Postgres metadata, benchmarks

Currently supported over TCP: `PING`, `SET`, `GET`, `DEL`, `EXPIRE`, `TTL`,
`KEYS`, `FLUSHALL`, `QUIT`.

## Why I built this

I wanted to understand how storage engines actually work under the hood —
not just use them. Building a small key-value store from scratch is the
fastest way to learn about in-memory data structures, concurrency, and
durability.

## Architecture
## Architecture
TCP client HTTP client
│ │
▼ ▼
┌─────────────┐ ┌─────────────────┐
│ KVHandler │ │ Flask admin │
│ (TCP :6379) │ │ (:8080) │
└──────┬──────┘ └────────┬────────┘
│ │
▼ ▼
┌─────────────┐ ┌─────────────────┐
│ KVStore │◄──────┤ /stats reads │
│ (in-memory) │ │ live state │
└──────┬──────┘ └─────────────────┘
│
▼
┌─────────────┐ ┌─────────────────┐
│ AOF log │ │ SQLite metadata│
│ (disk) │ │ (boots, stats) │
└─────────────┘ └─────────────────┘


Both servers run **in the same Python process**, sharing the same `KVStore`
instance.

## Durability design

Every **write** command (`SET`, `DEL`, `EXPIRE`, `FLUSHALL`) is appended to
`data/appendonly.aof` **before** it is applied to memory:

1. Client sends `SET name alice`
2. Server appends `SET name alice\n` to the AOF and calls `fsync` to force
   it to physical disk
3. Server applies the command to the in-memory dict

If the process is killed between steps 2 and 3, the command is still on
disk — on next startup the log is replayed and the state is rebuilt
correctly. This is the same core idea behind Redis's AOF mode and every
write-ahead-log-based database.

**Trade-off:** we `fsync` on every write for maximum durability, which is
slow (one disk flush per command). Real systems batch writes over a short
window (`appendfsync everysec` in Redis) to trade a small durability window
for much higher throughput.

### AOF compaction

Without compaction the log grows unbounded: `SET a 1`, `SET a 2`, ... `SET a
1000` writes 1000 lines even though only the last matters. A background
thread periodically rewrites the AOF to its minimal form — one `SET` per
live key, plus `EXPIRE` for keys with a TTL. The rewrite is atomic
(write to `.tmp`, then `os.replace`).

### TTL sweeping

Expired keys are removed two ways:

- **Lazily** — on read, if a key is past its expiry it is deleted before
  returning `(nil)`
- **Proactively** — a background thread calls `sweep_expired()` every
  second, so keys are removed even if never read again

This combination matches what Redis does in production.

## Quick start

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# or: source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
python -m app.server