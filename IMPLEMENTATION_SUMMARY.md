# FlipSide 2.0 - Implementation Summary (ARIA Fresh Start)

## Scope

The project is now a pure ARIA research application with a preserved 3D node interface and a retained decision graph workspace.

## Runtime flow

1. `src/main.tsx` boots `src/App3D.tsx`.
2. `src/FlipSide3D.tsx` drives two screens:
   - `src/components/GalaxySetupScene.tsx`
   - `src/components/DecisionGraphScene.tsx`
3. Launching research from galaxy setup calls `runAriaResearch`.
4. Returned claims/evidence seed the decision graph.

## Backend

`server/index.mjs` now exposes only ARIA routes:

- `GET /health`
- `POST /v1/research/run`
- `GET /v1/research`
- `GET /v1/research/:id`

Research runs persist to `server/data/research-runs.json`.

## Frontend data client

`src/lib/backendClient.ts` is ARIA-only and contains:

- `checkBackendHealth`
- `runAriaResearch`
- ARIA run/claim/evidence TypeScript types

## Removed legacy surface

Debate-era runtime/components/helpers were removed to complete the reset.

## Commands

```bash
npm install
npm run backend
npm run dev
npm run test -- --run
npm run build
```
