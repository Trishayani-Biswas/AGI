# FlipSide 2

FlipSide 2 is an AI-assisted debate app with:

- Finalized **Hexa Node** setup workflow (6-genre node map)
- Rich React/Vite frontend experience
- Local-first debate history and transcript exports
- Optional OpenAI or Anthropic API usage
- Backend debate endpoint for dynamic rebuttals (`/v1/debate`)
- Backend scaffold for production evolution (`/health`, history, multiplayer room creation, and webhooks)

## Final workflow (Hexa Node system)

1. **Galaxy Setup (Hexa Node Map)**: choose one of six genre nodes, then select a topic node.
2. **Solar Debate**: run timed rounds with AI rebuttals and per-round scoring.
3. **Cosmic Stats**: review final verdict, export transcript, and restart.

## Localhost setup (frontend + backend)

1. Install dependencies:

```bash
npm install
```

2. Create `.env` from `.env.example` and set values:

```text
VITE_BACKEND_URL=http://localhost:8787
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_API_KEY=your_anthropic_key
NEWS_API_KEY=your_newsapi_key
TESTING_AI_MODE=
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

In the Hexa Node setup flow, you can run in:

- **Backend + AI provider (primary)**: set backend URL; server uses `OPENAI_API_KEY` first, then `ANTHROPIC_API_KEY`
- **Direct key**: leave backend empty, provide key in-app (Anthropic direct mode in frontend)
- **Fallback**: no key configured, deterministic non-API responses

Testing options when you do not want paid API usage yet:

- **Mock AI mode (no key needed)**: set `TESTING_AI_MODE=mock` in `.env` for varied synthetic replies.
- **OpenAI-compatible provider mode**: set `OPENAI_API_KEY`, and if needed customize `OPENAI_BASE_URL` + `OPENAI_MODEL` for providers that offer trial/free tiers.

The setup UI also links key acquisition pages:

- OpenAI keys: https://platform.openai.com/api-keys
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
- `OPENAI_API_KEY` — optional backend OpenAI key (server-side, preferred)
- `OPENAI_BASE_URL` — optional OpenAI-compatible base URL (default `https://api.openai.com/v1`)
- `OPENAI_MODEL` — model name for OpenAI-compatible chat completions (default `gpt-4o-mini`)
- `OPENAI_SITE_URL` — optional referer header for compatible providers
- `OPENAI_APP_NAME` — optional app name header for compatible providers
- `ANTHROPIC_API_KEY` — optional backend Anthropic key (server-side)
- `NEWS_API_KEY` — optional backend NewsAPI key (server-side)
- `TESTING_AI_MODE` — set to `mock` to force local testing replies without external API calls
- `VITE_BACKEND_URL` — frontend backend base URL (enables `/v1/debate` usage)

## Build and quality checks

```bash
npm run lint
npm run test -- --run
npm run build
```

## Security notes

- `.env` files are gitignored. Keep all real keys there (or in deployment secrets), never in committed source.
- Setup-screen key inputs are masked and stored locally in your browser only when you choose direct mode.
- For production, prefer backend mode with server-side `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) and `NEWS_API_KEY`.

## Publish to GitHub (safe flow)

Before committing, make sure `.env` is not tracked:

```bash
git rm --cached .env
```

```bash
git init
git add .
git status
git commit -m "Stabilize app, secure key handling, and docs updates"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

If your repo already existed and ever had exposed keys, rotate those keys before pushing.
