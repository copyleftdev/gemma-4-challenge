#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from care_compass.config import STATIC_ROOT  # noqa: E402
from care_compass.errors import ValidationError  # noqa: E402
from care_compass.service import CareCompassService  # noqa: E402


SERVICE = CareCompassService()


class AppError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("content-length", "0"))
    if length <= 0:
        return {}
    body = handler.rfile.read(length)
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AppError(400, f"invalid JSON: {exc}") from exc


def content_type(path: Path) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
    }.get(path.suffix.lower(), "application/octet-stream")


def static_path(route: str) -> Path:
    path = (STATIC_ROOT / route.lstrip("/")).resolve()
    if not str(path).startswith(str(STATIC_ROOT.resolve())) or not path.exists():
        raise AppError(404, "not found")
    return path


class Handler(BaseHTTPRequestHandler):
    server_version = "CareCompass/0.1"

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_static(self, path: Path) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("content-type", content_type(path))
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/status":
                self.send_json(200, SERVICE.status_payload())
                return
            route = "/index.html" if parsed.path == "/" else parsed.path
            self.send_static(static_path(route))
        except AppError as exc:
            self.send_json(exc.status, {"ok": False, "error": exc.message})
        except Exception as exc:  # noqa: BLE001
            self.send_json(500, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path != "/api/decide":
                raise AppError(404, "not found")
            self.send_json(200, SERVICE.decide(read_body(self)))
        except AppError as exc:
            self.send_json(exc.status, {"ok": False, "error": exc.message})
        except ValidationError as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self.send_json(500, {"ok": False, "error": str(exc)})


def main() -> int:
    import os

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Care Compass listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

