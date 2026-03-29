# FlipSide 2.0 - Implementation Summary (Final Hexa Node Workflow)

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

## ⭐ 3D Galaxy UI

The app now features a fully interactive 3D Milky Way galaxy-themed UI:

### Entry Point
- `src/main.tsx` → `src/App3D.tsx` → `src/FlipSide3D.tsx`

### Three Screens
1. **Galaxy Setup Scene** (`src/components/GalaxySetupScene.tsx`)
   - Spiral galaxy with 12,000 particles using custom GLSL shaders
   - Humanoid robot at center with glowing eyes and animated core
   - Hexa Node genre ring (6 primary nodes) with connected topic nodes
   - Configuration panel for mode, side, timer settings

2. **Solar Debate Scene** (`src/components/SolarDebateScene.tsx`)
   - Selected topic as glowing sun at center
   - Rounds displayed as orbiting planets
   - Messages appear as asteroids
   - Timer, score display, and chat input overlaid

3. **Cosmic Stats Scene** (`src/components/CosmicStatsScene.tsx`)
   - Victory/defeat particles and symbols
   - Final scores with animations
   - Export transcript, share, play again options

## Final Workflow

1. Galaxy Setup (Hexa Node map): pick genre node -> pick topic node.
2. Solar Debate: run timed rounds with rebuttal generation and scoring.
3. Cosmic Stats: final verdict, transcript export, restart loop.

### 3D Libraries Added
- `@react-three/fiber` - React renderer for Three.js
- `@react-three/drei` - Useful helpers (Stars, Float, Html, Trail)
- `@react-three/postprocessing` - Post-processing effects
- `three` / `three-stdlib` - Core 3D library
- `maath` - Math utilities for 3D
- `framer-motion-3d` - 3D animations

## Original Frontend Structure

The original implementation (preserved):

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

## Environment Variables

Create `.env` file (copy from `.env.example`):
```
ANTHROPIC_API_KEY=your_key_here
NEWS_API_KEY=your_newsapi_key_here
VITE_BACKEND_URL=http://localhost:8787
```

⚠️ **Security**: `.env` files are gitignored. Never commit API keys!

## Development Commands

```bash
npm install        # Install dependencies (required after clone)
npm run dev        # Start frontend (port 5173)
npm run backend    # Start backend (port 8787)
npm run lint       # Run ESLint
npm run build      # Build for production
npm run test       # Run tests
```

## GitHub Push Commands

```bash
git rm --cached .env
git add -A
git commit -m "Finalize hexa-node workflow and secure env handling"
git push origin main
```
