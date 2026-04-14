# AGI Wiki Schema

This repository uses the Karpathy LLM Wiki pattern as a long-horizon memory layer for AGI experiments.

Reference pattern:
- https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## Architecture

Three-layer model:
1. Raw sources: immutable experiment artifacts under outputs/.
2. Wiki: maintained markdown under wiki/.
3. Schema: this file defines ingest, query, and lint rules.

## Directory Contract

- wiki/index.md: primary catalog page. Read this first.
- wiki/log.md: append-only chronology with headings in format:
  - ## [YYYY-MM-DD] ingest | <run_name>
- wiki/runs/<run_name>.md: per-run normalized snapshots.
- wiki/concepts/hypotheses.md: current hypothesis outcomes.
- wiki/concepts/interventions.md: prioritized interventions.
- wiki/concepts/campaign_state.md: campaign-level state summary.

## Ingest Rules

When ingesting new run outputs:
1. Never modify files under outputs/.
2. Update wiki/runs/<run_name>.md.
3. Update wiki/index.md catalog.
4. Append new entry to wiki/log.md (do not rewrite old entries).
5. Update concept pages if campaign evidence changed.
6. Keep links relative and working.

## Query Rules

When answering questions:
1. Read wiki/index.md first.
2. Read the most relevant concept page(s).
3. Drill into run pages for evidence.
4. Cite run page paths and key metrics explicitly.

## Lint Rules

Run periodic wiki health checks:
1. Broken links.
2. Orphan run pages not linked from index.
3. Claims in concept pages without run evidence.
4. Stale interventions contradicted by new data.

## Local Workflow Commands

Build wiki once:

```bash
.venv/bin/python scripts/build_agi_wiki.py --outputs-dir outputs --wiki-dir wiki --max-runs 30
```

Maintain wiki in watch mode:

```bash
.venv/bin/python scripts/build_agi_wiki.py --outputs-dir outputs --wiki-dir wiki --max-runs 30 --watch --watch-interval 20
```
