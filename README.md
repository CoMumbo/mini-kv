# mini-kv

A small Redis-like key-value store written in Python, with a TCP protocol,
thread-safe in-memory storage, TTL support, and **append-only file (AOF)
persistence with crash recovery**.

## Status

✅ Core server working
✅ AOF persistence + replay-on-startup crash recovery
🚧 TTL sweeper thread, AOF compaction, Postgres metadata, Flask admin endpoints

Currently supported: `PING`, `SET`, `GET`, `DEL`, `EXPIRE`, `TTL`, `KEYS`,
`FLUSHALL`, `QUIT` over a line-based TCP protocol.

## Why I built this

I wanted to understand how storage engines actually work under the hood —
not just use them. Building a small key-value store from scratch is the
fastest way to learn about in-memory data structures, concurrency, and
durability.

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

On startup:

1. Server opens the AOF
2. Reads every line, in order
3. Dispatches each line to the store (with logging disabled, to avoid
   appending duplicates)
4. Then starts accepting client connections

**Trade-off:** we `fsync` on every write for maximum durability, which is
slow (one disk flush per command). Real systems batch writes over a short
window (`appendfsync everysec` in Redis) to trade a small durability window
for much higher throughput. Documented in `docs/DESIGN.md`.

## Quick start

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# or: source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
python -m app.server