# FlipSide 2

FlipSide 2 is an AI-assisted debate app with:

- Rich React/Vite frontend experience
- Local-first debate history and transcript exports
- Optional Gemini API usage
- Backend scaffold for production evolution (`/health`, history, multiplayer room creation, and webhooks)

## Run locally

Install dependencies:

```bash
npm install
```

Start frontend:

```bash
npm run dev
```

Start backend API (new terminal):

```bash
npm run backend
```

Default backend address is `http://localhost:8787`.

In the app setup screen, set **Future Backend URL** to:

```text
http://localhost:8787
```

Then use:

- **Import API** to load history from backend
- **Sync API** to push local history to backend
- **Create Room** (Multiplayer Beta) to create a backend-backed room code

## API scaffold

- `GET /health` — health check
- `GET /v1/history` — fetch saved debates
- `POST /v1/history` — save one or many debates
- `POST /v1/multiplayer/rooms` — create a multiplayer room
- `POST /v1/webhooks/events` — ingest events (`X-Api-Key` required only if `WEBHOOK_SECRET` is set)

Data persists to JSON files in `server/data/` (gitignored).

## Environment variables

- `PORT` — backend port (default `8787`)
- `CORS_ORIGIN` — allowed origin for backend CORS (default `*`)
- `WEBHOOK_SECRET` — optional API key required by webhook endpoint
- `VITE_GEMINI_API_KEY` — optional frontend default Gemini key

## Build and quality checks

```bash
npm run lint
npm run build
```
