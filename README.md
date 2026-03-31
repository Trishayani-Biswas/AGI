# ARIA — Adversarial Research Intelligence Architecture

**Status:** Reset & Scaffolded (March 31, 2026)  
**Frontend:** React 19 + TypeScript + Vite  
**Backend:** (To be implemented)

ARIA is a multi-agent adversarial research system that orchestrates four specialized agents to investigate topics from opposing perspectives:

- **Advocate** – finds supporting evidence (pro-framing searches)
- **Skeptic** – finds contradictions and critiques (counter-framing)
- **Domain** – grounds in academic/technical baseline (scholarly sources)
- **Arbitrator** – synthesizes findings and scores confidence gaps

## Quick Start

```bash
npm install
npm run dev
```

Open <http://localhost:5173>

## Build

```bash
npm run build
npm run preview
```

## Project Structure

```text
src/
├── components/          # React components (build to spec)
├── pages/              # Page-level components
├── hooks/              # Custom hooks (useResearch, etc.)
├── services/
│   ├── types.ts        # TypeScript API types  
│   └── ariaClient.ts   # Typed HTTP client
└── App.tsx
tests/fixtures/         # Mock API responses for testing
```

## Key Documents

- **[PROJECT_SPEC.md](PROJECT_SPEC.md)** – Frozen specification for backend API & frontend features
- **[FRONTEND_WORKFLOW.md](FRONTEND_WORKFLOW.md)** – How to request features and components from GitHub Copilot
- **[.env.example](.env.example)** – Environment variables template

## Development Workflow

### Phase 1: Isolation (Build with Mock Data)

Start with components rendered against fixtures from `tests/fixtures/`:

```bash
npm run dev
```

Test components with hardcoded mock data before backend integration.

### Phase 2: Integration (Connect to Backend)

Once backend API is live, integrate via the `ariaClient` and `useResearch` hook:

```typescript
const { data, loading, error } = useResearch(requestId);
```

### Phase 3: Polish (Styling & UX)

Add error states, loading states, responsive design, and accessibility.

## UI Checklist

Use this checklist before merging UI changes:

- Keep layout and component styling in CSS files, not inline style props.
- Preserve fullscreen 3D canvas behavior in `App` + `GalacticSpace`.
- Keep navigation controls working: drag to orbit + `▲ ◄ ► ▼` buttons.
- Keep the camera position readout visible and updating.
- Maintain cross-browser glass effects with both `backdrop-filter` and `-webkit-backdrop-filter`.
- Run `npm run build` and ensure it passes before committing.

## Testing

```bash
npm test                 # Run all tests
npm test -- AgentPanel   # Run specific component test
npm run test:ui         # Open Vitest UI
```

## Environment Variables

Copy `.env.example` to `.env.local` and configure:

```env
VITE_BACKEND_URL=http://localhost:8000
```

## Next Steps

1. Review **PROJECT_SPEC.md** for the full technical specification
2. Check **FRONTEND_WORKFLOW.md** for how to request components
3. Start with Phase 1: build components isolated with mock data
4. Wait for backend implementation before Phase 2 integration
