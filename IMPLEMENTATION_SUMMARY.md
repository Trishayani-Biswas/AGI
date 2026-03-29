# FlipSide 2.0 - Implementation Summary (Current State)

## Quick Start

```bash
cd "c:\Users\jitpa\OneDrive\Documents\JIT\PROJECTS\Formal\flipside2"
npm install
npm run dev
```

Optional backend (separate terminal):

```bash
npm run backend
```

Frontend runs on Vite default (`http://localhost:5173`).
Backend default port is `8787` (configurable via `PORT`).

## Current App Entry

`src/main.tsx` already uses:

```tsx
import App from './AppNew'
```

`src/AppNew.tsx` renders `FlipSide2` inside an error boundary.

## Current Frontend Structure

The current implementation is centered around:

- `src/FlipSide2.tsx` - main UI flow (setup, debate, stats)
- `src/lib/useDebate.ts` - debate state management
- `src/lib/useTimer.ts` - timer logic
- `src/lib/useToast.ts` - toast notifications
- `src/lib/useLocalStorage.ts` - persistent client state
- `src/lib/backendClient.ts` - backend + model request helpers
- `src/lib/storage.ts` - local history/session persistence
- `src/lib/scoring.ts` - scoring and verdict helpers
- `src/lib/types.ts` - shared TypeScript types

## Backend Summary

`server/index.mjs` exposes:

- `GET /health`
- `GET /v1/history`
- `POST /v1/history`
- `POST /v1/multiplayer/rooms`
- `POST /v1/webhooks/events`
- `POST /v1/debate`

Data files are persisted under `server/data/` (gitignored).

## Development Commands

```bash
npm run dev
npm run backend
npm run lint
npm run build
npm run test
```
