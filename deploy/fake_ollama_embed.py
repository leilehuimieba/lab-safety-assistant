#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


VECTOR_SIZE = 1024
HOST = "0.0.0.0"
PORT = 11434


def build_embedding(text: str) -> list[float]:
    text = text or ""
    seed = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
    numbers: list[float] = []
    # Expand deterministic bytes to VECTOR_SIZE floats in [-1, 1].
    block = seed
    while len(numbers) < VECTOR_SIZE:
        block = hashlib.sha256(block + seed).digest()
        for idx in range(0, len(block), 2):
            if len(numbers) >= VECTOR_SIZE:
                break
            chunk = block[idx : idx + 2]
            if len(chunk) < 2:
                continue
            value = int.from_bytes(chunk, "big", signed=False)
            normalized = (value / 65535.0) * 2.0 - 1.0
            numbers.append(round(normalized, 6))
    return numbers


def normalize_inputs(payload: dict[str, Any]) -> list[str]:
    if isinstance(payload.get("input"), list):
        return [str(x) for x in payload.get("input") or []]
    if payload.get("input") is not None:
        return [str(payload.get("input"))]
    if payload.get("prompt") is not None:
        return [str(payload.get("prompt"))]
    return [""]


class Handler(BaseHTTPRequestHandler):
    server_version = "fake-ollama-embed/1.0"

    def _send_json(self, code: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/tags"):
            self._send_json(
                200,
                {
                    "models": [
                        {
                            "name": "bge-m3",
                            "model": "bge-m3",
                            "modified_at": "2026-01-01T00:00:00Z",
                            "size": 0,
                        }
                    ]
                },
            )
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if not (self.path.startswith("/api/embed") or self.path.startswith("/api/embeddings")):
            self._send_json(404, {"error": "not_found"})
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        model = str(payload.get("model") or "bge-m3")
        texts = normalize_inputs(payload)
        embeddings = [build_embedding(text) for text in texts]
        self._send_json(200, {"model": model, "embeddings": embeddings})


def main() -> int:
    server = HTTPServer((HOST, PORT), Handler)
    print(f"fake ollama embedding server listening on {HOST}:{PORT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
