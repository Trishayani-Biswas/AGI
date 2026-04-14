from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple


_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _score_document(content: str, query_tokens: List[str]) -> int:
    lowered = content.lower()
    return sum(lowered.count(token) for token in query_tokens)


def _page_priority(path: Path) -> int:
    parts = set(path.parts)
    if "concepts" in parts:
        return 3
    if path.name == "index.md":
        return 2
    if "runs" in parts:
        return 1
    return 0


def _best_snippet(content: str, query_tokens: List[str], snippet_chars: int) -> str:
    lowered = content.lower()
    positions = [lowered.find(token) for token in query_tokens if lowered.find(token) >= 0]
    if not positions:
        trimmed = content.strip().replace("\n", " ")
        return trimmed[:snippet_chars]

    center = min(positions)
    start = max(0, center - (snippet_chars // 3))
    end = min(len(content), start + snippet_chars)
    snippet = content[start:end].replace("\n", " ").strip()
    return snippet


def query_wiki(
    wiki_dir: Path,
    query: str,
    top_k: int,
    snippet_chars: int,
    include_log: bool,
) -> List[Tuple[Path, int, str]]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    results: List[Tuple[Path, int, str]] = []
    for md_path in sorted(wiki_dir.rglob("*.md")):
        if not md_path.is_file():
            continue
        if (not include_log) and md_path.name == "log.md":
            continue
        try:
            content = md_path.read_text(encoding="utf-8")
        except OSError:
            continue

        score = _score_document(content, query_tokens)
        if score <= 0:
            continue

        score += _page_priority(md_path)

        snippet = _best_snippet(content=content, query_tokens=query_tokens, snippet_chars=snippet_chars)
        results.append((md_path, score, snippet))

    results.sort(key=lambda item: (item[1], -len(item[2])), reverse=True)
    return results[:max(1, top_k)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search AGI wiki markdown pages")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("--wiki-dir", type=str, default="wiki", help="Path to wiki directory")
    parser.add_argument("--top-k", type=int, default=8, help="Max number of results")
    parser.add_argument("--snippet-chars", type=int, default=220, help="Snippet length per result")
    parser.add_argument("--include-log", action="store_true", help="Include wiki/log.md in search results")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wiki_dir = Path(args.wiki_dir)

    results = query_wiki(
        wiki_dir=wiki_dir,
        query=args.query,
        top_k=args.top_k,
        snippet_chars=max(80, args.snippet_chars),
        include_log=bool(args.include_log),
    )

    if not results:
        print("No wiki matches found.")
        return

    print(f"Query: {args.query}")
    print(f"Wiki: {wiki_dir}")
    print("")

    for idx, (path, score, snippet) in enumerate(results, start=1):
        rel = path
        try:
            rel = path.relative_to(Path.cwd())
        except ValueError:
            rel = path
        print(f"{idx}. {rel.as_posix()} (score={score})")
        print(f"   {snippet}")


if __name__ == "__main__":
    main()
