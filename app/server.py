import socketserver
import logging
from app.protocol import parse, encode, ProtocolError
from app.store import KVStore
from app.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mini-kv")

STORE = KVStore()


class KVHandler(socketserver.StreamRequestHandler):
    def handle(self):
        peer = self.client_address
        log.info("client connected: %s", peer)
        try:
            for raw in self.rfile:
                line = raw.decode("utf-8", errors="replace")
                try:
                    response = self.dispatch(line)
                except ProtocolError as e:
                    response = f"ERR {e}\n"
                self.wfile.write(response.encode("utf-8"))
                if line.strip().upper() == "QUIT":
                    break
        except ConnectionResetError:
            pass
        finally:
            log.info("client disconnected: %s", peer)

    def dispatch(self, line: str) -> str:
        cmd, args = parse(line)

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


class KVServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    with KVServer((Config.HOST, Config.PORT), KVHandler) as server:
        log.info("mini-kv listening on %s:%s", Config.HOST, Config.PORT)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("shutting down")


if __name__ == "__main__":
    main()