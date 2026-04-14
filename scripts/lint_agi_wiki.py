from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _is_external_link(link: str) -> bool:
    lowered = link.lower().strip()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("mailto:")
        or lowered.startswith("#")
    )


def _normalize_link_target(link: str) -> str:
    clean = link.strip()
    if "#" in clean:
        clean = clean.split("#", 1)[0]
    if "?" in clean:
        clean = clean.split("?", 1)[0]
    return clean


def _extract_markdown_links(markdown_text: str) -> List[str]:
    return [match.group(1) for match in _LINK_RE.finditer(markdown_text)]


def lint_wiki(wiki_dir: Path) -> Dict[str, object]:
    markdown_files = sorted(path for path in wiki_dir.rglob("*.md") if path.is_file())

    broken_links: List[Tuple[Path, str, Path]] = []
    referenced_run_pages: Set[Path] = set()

    for md_path in markdown_files:
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue

        for raw_link in _extract_markdown_links(text):
            if _is_external_link(raw_link):
                continue

            target = _normalize_link_target(raw_link)
            if not target:
                continue

            target_path = (md_path.parent / target).resolve()
            if not target_path.exists():
                broken_links.append((md_path, raw_link, target_path))
                continue

            if target_path.is_file() and target_path.parent.name == "runs" and target_path.suffix == ".md":
                referenced_run_pages.add(target_path)

    run_pages_dir = wiki_dir / "runs"
    all_run_pages = set(path.resolve() for path in run_pages_dir.glob("*.md") if path.is_file()) if run_pages_dir.exists() else set()
    orphan_run_pages = sorted(path for path in all_run_pages if path not in referenced_run_pages)

    return {
        "wiki_dir": str(wiki_dir),
        "markdown_files": len(markdown_files),
        "broken_links": broken_links,
        "orphan_run_pages": orphan_run_pages,
    }


def build_report(result: Dict[str, object], report_path: Path) -> None:
    markdown_files = int(result.get("markdown_files", 0))
    broken_links = result.get("broken_links", [])
    orphan_run_pages = result.get("orphan_run_pages", [])
    wiki_dir = Path(str(result.get("wiki_dir", "wiki")))

    lines: List[str] = []
    lines.append("# AGI Wiki Lint Report")
    lines.append("")
    lines.append(f"- Wiki directory: {wiki_dir}")
    lines.append(f"- Markdown files scanned: {markdown_files}")
    lines.append(f"- Broken links: {len(broken_links)}")
    lines.append(f"- Orphan run pages: {len(orphan_run_pages)}")
    lines.append("")

    lines.append("## Broken Links")
    lines.append("")
    if not broken_links:
        lines.append("No broken links found.")
    else:
        lines.append("| Source File | Link | Resolved Target |")
        lines.append("| --- | --- | --- |")
        for src, link, target in broken_links:
            src_rel = src.relative_to(wiki_dir.parent)
            target_rel = target
            try:
                target_rel = target.relative_to(wiki_dir.parent)
            except ValueError:
                target_rel = target
            lines.append(f"| {src_rel.as_posix()} | {link} | {str(target_rel).replace('|', '%7C')} |")

    lines.append("")
    lines.append("## Orphan Run Pages")
    lines.append("")
    if not orphan_run_pages:
        lines.append("No orphan run pages found.")
    else:
        for path in orphan_run_pages:
            rel = path
            try:
                rel = path.relative_to(wiki_dir.parent)
            except ValueError:
                rel = path
            lines.append(f"- {Path(rel).as_posix()}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint AGI wiki links and structure")
    parser.add_argument("--wiki-dir", type=str, default="wiki", help="Path to wiki directory")
    parser.add_argument(
        "--report-path",
        type=str,
        default="wiki/lint_report.md",
        help="Path to markdown lint report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wiki_dir = Path(args.wiki_dir)
    report_path = Path(args.report_path)

    result = lint_wiki(wiki_dir=wiki_dir)
    build_report(result=result, report_path=report_path)

    broken_links = result.get("broken_links", [])
    orphan_run_pages = result.get("orphan_run_pages", [])
    print(
        "Wiki lint complete: "
        f"broken_links={len(broken_links)} "
        f"orphan_run_pages={len(orphan_run_pages)} "
        f"report={report_path}"
    )


if __name__ == "__main__":
    main()
