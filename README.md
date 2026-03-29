# FlipSide 2 (ARIA Edition)

FlipSide 2 is now an ARIA-focused research and decision system with a 3D node interface.

## Product flow

1. Galaxy setup: choose a topic from the 3D node map.
2. ARIA research run: orchestrate Advocate, Skeptic, Domain, and Arbitrator outputs.
3. Decision graph: auto-seed claims/evidence and continue mapping decisions manually.

## Run locally

```bash
npm install
npm run backend
npm run dev
```

Default URLs:

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:8787>

## Backend API

- `GET /health`
- `POST /v1/research/run`
- `GET /v1/research?limit=10`
- `GET /v1/research/:id`

Persisted runs are stored in `server/data/research-runs.json`.

## Environment variables

- `PORT` (default `8787`)
- `CORS_ORIGIN` (default `*`)
- `VITE_BACKEND_URL` (frontend backend base URL)

## Verify quality

```bash
npm run lint
npm run test -- --run
npm run build
```
