import socketserver
import threading
import logging
import time
from app.protocol import parse, encode, ProtocolError
from app.store import KVStore
from app.persistence import AOF
from app.ttl import TTLSweeper
from app.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mini-kv")

# --- Global state -----------------------------------------------------------

STORE = KVStore()
AOF_LOG = AOF(Config.AOF_PATH)
SWEEPER = TTLSweeper(STORE, interval=Config.TTL_SWEEP_INTERVAL)


# --- Command dispatch -------------------------------------------------------

WRITE_COMMANDS = {"SET", "DEL", "EXPIRE", "FLUSHALL"}


def dispatch(line: str, *, log_write: bool) -> str:
    """Parse and execute one command. Optionally append writes to AOF."""
    cmd, args = parse(line)

    if log_write and cmd in WRITE_COMMANDS:
        AOF_LOG.append(line)

    if cmd == "PING":
        return encode("PONG")
    if cmd == "SET":
        if len(args) != 2:
            raise ProtocolError("SET requires key and value")
        STORE.set(args[0], args[1])
        return encode("OK")
    if cmd == "GET":
        if len(args) != 1:
            raise ProtocolError("GET requires key")
        return encode(STORE.get(args[0]))
    if cmd == "DEL":
        if len(args) != 1:
            raise ProtocolError("DEL requires key")
        return encode(STORE.delete(args[0]))
    if cmd == "EXPIRE":
        if len(args) != 2:
            raise ProtocolError("EXPIRE requires key and seconds")
        return encode(STORE.expire(args[0], int(args[1])))
    if cmd == "TTL":
        if len(args) != 1:
            raise ProtocolError("TTL requires key")
        return encode(STORE.ttl(args[0]))
    if cmd == "KEYS":
        return encode(STORE.keys())
    if cmd == "FLUSHALL":
        STORE.flush()
        return encode("OK")
    if cmd == "QUIT":
        return encode("OK")

    raise ProtocolError(f"unknown command '{cmd}'")


def replay_aof() -> int:
    lines = AOF_LOG.replay()
    for line in lines:
        try:
            dispatch(line, log_write=False)
        except ProtocolError as e:
            log.warning("skipping bad AOF line %r: %s", line, e)
    return len(lines)


# --- AOF compaction thread --------------------------------------------------

class AOFCompactor:
    """Periodically rewrite the AOF to its minimal form."""

    def __init__(self, aof: AOF, store: KVStore, interval: float):
        self.aof = aof
        self.store = store
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="aof-compactor", daemon=True)
        self._thread.start()
        log.info("AOF compactor started (interval=%.0fs)", self.interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            log.info("AOF compactor stopped")

    def _run(self) -> None:
        while not self._stop.is_set():
            self._stop.wait(self.interval)
            if self._stop.is_set():
                return
            try:
                before = len(self.aof.replay())
                n = self.aof.compact(self.store.snapshot(), self.store.expires_snapshot())
                if before != n:
                    log.info("compacted AOF: %d -> %d lines", before, n)
            except Exception:
                log.exception("AOF compactor error")


COMPACTOR = AOFCompactor(AOF_LOG, STORE, interval=Config.COMPACT_INTERVAL)


# --- TCP server -------------------------------------------------------------

class KVHandler(socketserver.StreamRequestHandler):
    def handle(self):
        peer = self.client_address
        log.info("client connected: %s", peer)
        try:
            for raw in self.rfile:
                line = raw.decode("utf-8", errors="replace")
                try:
                    response = dispatch(line, log_write=True)
                except ProtocolError as e:
                    response = f"ERR {e}\n"
                except ValueError as e:
                    response = f"ERR {e}\n"
                self.wfile.write(response.encode("utf-8"))
                if line.strip().upper() == "QUIT":
                    break
        except ConnectionResetError:
            pass
        finally:
            log.info("client disconnected: %s", peer)


class KVServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    replayed = replay_aof()
    log.info("replayed %d commands from AOF", replayed)

    SWEEPER.start()
    COMPACTOR.start()

    with KVServer((Config.HOST, Config.PORT), KVHandler) as server:
        log.info("mini-kv listening on %s:%s", Config.HOST, Config.PORT)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("shutting down")
        finally:
            SWEEPER.stop()
            COMPACTOR.stop()
            AOF_LOG.close()


if __name__ == "__main__":
    main()