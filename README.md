# FlipSide 2

FlipSide 2 is an AI-assisted debate app with:

- Rich React/Vite frontend experience
- Local-first debate history and transcript exports
- Optional Anthropic API usage
- Backend debate endpoint for dynamic rebuttals (`/v1/debate`)
- Backend scaffold for production evolution (`/health`, history, multiplayer room creation, and webhooks)

## Localhost setup (frontend + backend)

1. Install dependencies:

```bash
npm install
```

2. Create `.env` from `.env.example` and set values:

```text
VITE_BACKEND_URL=http://localhost:8787
ANTHROPIC_API_KEY=your_anthropic_key
NEWS_API_KEY=your_newsapi_key
CORS_ORIGIN=http://localhost:5173
PORT=8787
```

3. Start backend API (terminal 1):

```bash
npm run backend
```

4. Start frontend (terminal 2):

```bash
npm run dev
```

Expected local URLs:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8787/health`
- Debate endpoint: `http://localhost:8787/v1/debate`
- News endpoint: `http://localhost:8787/v1/news?q=ai&limit=6`

In the setup screen, you can run in:

- **Backend + Anthropic (primary)**: set backend URL; server uses `ANTHROPIC_API_KEY`
- **Direct Anthropic key**: leave backend empty, provide key in-app
- **Fallback**: no key configured, deterministic non-API responses

The setup UI also links key acquisition pages:

- Anthropic keys: https://console.anthropic.com/settings/keys
- NewsAPI keys: https://newsapi.org/register

## API scaffold

- `GET /health` — health check
- `GET /v1/history` — fetch saved debates
- `POST /v1/history` — save one or many debates
- `POST /v1/multiplayer/rooms` — create a multiplayer room
- `POST /v1/webhooks/events` — ingest events (`X-Api-Key` required only if `WEBHOOK_SECRET` is set)
- `POST /v1/debate` — generate a real-time debate reply
- `GET /v1/news?q=...&limit=...` — retrieve news topic suggestions (NewsAPI + deterministic fallback)

Data persists to JSON files in `server/data/` (gitignored).

## Environment variables

- `PORT` — backend port (default `8787`)
- `CORS_ORIGIN` — allowed origin for backend CORS (default `*`)
- `WEBHOOK_SECRET` — optional API key required by webhook endpoint
- `ANTHROPIC_API_KEY` — optional backend Anthropic key (server-side)
- `NEWS_API_KEY` — optional backend NewsAPI key (server-side)
- `VITE_BACKEND_URL` — frontend backend base URL (enables `/v1/debate` usage)

## Build and quality checks

```bash
npm run lint
npm run build
```
