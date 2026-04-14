---
description: "Ingest one NEAT run into the AGI wiki and update index/log/pages"
name: "Wiki Ingest Run"
argument-hint: "<run-folder-name-or-path>"
agent: "agent"
---
Ingest the provided run source into the AGI wiki using [AGI_WIKI schema](../../AGI_WIKI.md).

Requirements:
- Treat outputs files as immutable sources.
- Update the corresponding wiki run page.
- Update wiki/index.md catalog references.
- Append an entry to wiki/log.md in the required heading format.
- If the run changes campaign conclusions, update concept pages:
  - wiki/concepts/campaign_state.md
  - wiki/concepts/hypotheses.md
  - wiki/concepts/interventions.md
- Keep links relative and ensure no broken links.

Return a short summary with:
- pages changed
- key metric deltas
- whether intervention priorities changed
