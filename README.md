# mini-kv

A small Redis-like key-value store written in Python, with a TCP protocol,
thread-safe in-memory storage, and TTL support.

## Status

🚧 In progress — building an append-only persistence layer next.

Currently supported: `PING`, `SET`, `GET`, `DEL`, `EXPIRE`, `TTL`, `KEYS`,
`FLUSHALL`, `QUIT` over a line-based TCP protocol.

## Why I built this

I wanted to understand how storage engines actually work under the hood —
not just use them. Building a small key-value store from scratch is the
fastest way to learn about in-memory data structures, concurrency, and
(later) durability and crash recovery.

## Quick start

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# or: source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
python -m app.server