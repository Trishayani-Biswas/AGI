from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

from query_agi_wiki import query_wiki


def _parse_bool(raw: str, default: bool) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _safe_int(raw: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def _results_payload(
    wiki_dir: Path,
    query: str,
    top_k: int,
    snippet_chars: int,
    include_log: bool,
) -> Dict[str, Any]:
    results = query_wiki(
        wiki_dir=wiki_dir,
        query=query,
        top_k=top_k,
        snippet_chars=snippet_chars,
        include_log=include_log,
    )

    items: List[Dict[str, Any]] = []
    for path, score, snippet in results:
        rel = path
        try:
            rel = path.relative_to(Path.cwd())
        except ValueError:
            rel = path
        items.append(
            {
                "path": rel.as_posix(),
                "score": int(score),
                "snippet": snippet,
            }
        )

    return {
        "query": query,
        "wiki_dir": wiki_dir.as_posix(),
        "count": len(items),
        "results": items,
    }


class WikiQueryHandler(BaseHTTPRequestHandler):
    wiki_dir: Path = Path("wiki")
    default_top_k: int = 8
    default_snippet_chars: int = 220
    default_include_log: bool = False

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "wiki-query-api",
                    "wiki_dir": self.wiki_dir.as_posix(),
                },
            )
            return

        if parsed.path != "/query":
            self._send_json(404, {"error": "Not found"})
            return

        params = parse_qs(parsed.query)
        query = params.get("q", params.get("query", [""]))[0].strip()
        if not query:
            self._send_json(400, {"error": "Missing query string parameter: q"})
            return

        top_k = _safe_int(
            params.get("top_k", [str(self.default_top_k)])[0],
            default=self.default_top_k,
            minimum=1,
            maximum=50,
        )
        snippet_chars = _safe_int(
            params.get("snippet_chars", [str(self.default_snippet_chars)])[0],
            default=self.default_snippet_chars,
            minimum=80,
            maximum=2000,
        )
        include_log = _parse_bool(
            params.get("include_log", [str(self.default_include_log)])[0],
            default=self.default_include_log,
        )

        payload = _results_payload(
            wiki_dir=self.wiki_dir,
            query=query,
            top_k=top_k,
            snippet_chars=snippet_chars,
            include_log=include_log,
        )
        self._send_json(200, payload)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/query":
            self._send_json(404, {"error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return

        raw_body = self.rfile.read(max(0, content_length))
        try:
            payload = json.loads(raw_body.decode("utf-8") if raw_body else "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        if not isinstance(payload, dict):
            self._send_json(400, {"error": "JSON body must be an object"})
            return

        query = str(payload.get("query", payload.get("q", ""))).strip()
        if not query:
            self._send_json(400, {"error": "Missing query field"})
            return

        top_k_raw = str(payload.get("top_k", self.default_top_k))
        snippet_chars_raw = str(payload.get("snippet_chars", self.default_snippet_chars))
        include_log_raw = str(payload.get("include_log", self.default_include_log))

        top_k = _safe_int(top_k_raw, default=self.default_top_k, minimum=1, maximum=50)
        snippet_chars = _safe_int(
            snippet_chars_raw,
            default=self.default_snippet_chars,
            minimum=80,
            maximum=2000,
        )
        include_log = _parse_bool(include_log_raw, default=self.default_include_log)

        result = _results_payload(
            wiki_dir=self.wiki_dir,
            query=query,
            top_k=top_k,
            snippet_chars=snippet_chars,
            include_log=include_log,
        )
        self._send_json(200, result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tiny HTTP API over AGI wiki query")
    parser.add_argument("--wiki-dir", type=str, default="wiki", help="Path to wiki directory")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    parser.add_argument("--top-k", type=int, default=8, help="Default max number of results")
    parser.add_argument("--snippet-chars", type=int, default=220, help="Default snippet length")
    parser.add_argument("--include-log", action="store_true", help="Include wiki/log.md by default")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    class ConfiguredWikiQueryHandler(WikiQueryHandler):
        wiki_dir = Path(args.wiki_dir)
        default_top_k = max(1, min(50, int(args.top_k)))
        default_snippet_chars = max(80, min(2000, int(args.snippet_chars)))
        default_include_log = bool(args.include_log)

    server = ThreadingHTTPServer((args.host, int(args.port)), ConfiguredWikiQueryHandler)
    print(
        "Wiki query API listening: "
        f"http://{args.host}:{args.port} "
        f"wiki_dir={Path(args.wiki_dir).as_posix()}"
    )
    print("Endpoints: GET /health, GET /query?q=..., POST /query")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping wiki query API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
