"""Serve the static dashboard and Vercel API together for local testing."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.analyze import handler as ApiHandler


class DevHandler(ApiHandler, SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/analyze":
            return ApiHandler.do_GET(self)
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path.split("?", 1)[0] == "/api/analyze":
            return ApiHandler.do_POST(self)
        self.send_error(405, "POST is only supported at /api/analyze")


def main():
    port = 4173
    server = ThreadingHTTPServer(
        ("127.0.0.1", port),
        partial(DevHandler, directory=str(ROOT_DIR)),
    )
    print(f"HDFS dashboard running at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
