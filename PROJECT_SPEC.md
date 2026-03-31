# ARIA Frontend + Backend Specification

**Status:** Ready for Implementation  
**Reset Date:** March 31, 2026  
**Last Updated:** March 31, 2026

---

## 1. Project Overview

ARIA is a **multi-agent adversarial research system** that orchestrates four specialized agents via LangGraph to investigate topics from opposing perspectives:

- **Advocate**: Finds supporting evidence (pro-framing searches via Tavily)
- **Skeptic**: Finds contradictions and critiques (counter-framing searches)
- **Domain**: Grounds findings in academic/technical baseline (arxiv, scholar, gov domains)
- **Arbitrator**: Synthesizes outputs and scores confidence gaps (no search, pure synthesis)

**Non-Goals:**
- ❌ Not a chatbot or conversational AI
- ❌ Not a RAG wrapper
- ❌ Not a single-model summarizer
- ❌ Never flatten four agents into one prompt

---

## 2. Tech Stack

### Backend
- **Runtime**: Node.js or Python (to be selected)
- **Orchestration**: LangGraph (multi-agent state graph)
- **Search API**: Tavily (with keyword, counter, and domain-filtered queries)
- **LLM**: (API to be specified—Gemini, OpenAI, Claude, etc.)
- **HTTP Framework**: FastAPI (Python) or Express/Hono (Node.js)
- **Persistence**: JSON file or SQLite (research-runs.json initially)
- **Environment**: Manage keys via `.env`, never in source

### Frontend
- **Framework**: React 19.2.4 with TypeScript
- **Build Tool**: Vite 8.0.1
- **Styling**: Tailwind CSS (basic setup, can add later)
- **State**: React hooks (useContext optional, useReducer if complex)
- **HTTP Client**: Fetch API + custom ariaClient wrapper with retry logic
- **Testing**: Vitest + React Testing Library

---

## 3. API Contract (Backend)

### Endpoints

#### POST /v1/research/start
**Request:**
```json
{
  "topic": "string",
  "query": "string"
}
```

**Response:**
```json
{
  "request_id": "uuid",
  "status": "queued",
  "created_at": "iso-timestamp"
}
```

#### GET /v1/research/{request_id}
**Response when in-progress:**
```json
{
  "request_id": "uuid",
  "status": "running",
  "progress": 0.5
}
```

**Response when complete:**
```json
{
  "request_id": "uuid",
  "status": "complete",
  "topic": "string",
  "results": {
    "advocate": {
      "findings": ["finding1", "finding2"],
      "confidence": 0.85,
      "sources": ["url1", "url2"],
      "raw_output": "string"
    },
    "skeptic": {
      "findings": ["counter1", "counter2"],
      "confidence": 0.72,
      "sources": ["url3", "url4"],
      "raw_output": "string"
    },
    "domain": {
      "findings": ["baseline1", "baseline2"],
      "confidence": 0.90,
      "sources": ["arxiv-url1", "scholar-url1"],
      "raw_output": "string"
    },
    "arbitrator": {
      "synthesis": "overall summary text",
      "confidence_score": 0.82,
      "gaps_identified": ["gap1", "gap2"],
      "recommendation": "string"
    }
  },
  "completed_at": "iso-timestamp"
}
```

#### GET /v1/research?limit=10&offset=0
**Response:**
```json
{
  "total": 42,
  "limit": 10,
  "offset": 0,
  "runs": [
    {
      "request_id": "uuid",
      "topic": "string",
      "status": "complete",
      "created_at": "iso-timestamp"
    }
  ]
}
```

#### GET /health
**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## 4. Frontend Architecture

### Directory Structure
```
src/
├── components/
│   ├── ResearchForm.tsx          # Topic + query input
│   ├── AgentPanel.tsx            # One agent output card
│   ├── ArbitratorSummary.tsx     # Final synthesis view
│   ├── ResearchList.tsx          # Past runs list
│   ├── LoadingState.tsx          # Spinner + status
│   └── ErrorBoundary.tsx         # Error handling
├── pages/
│   ├── Dashboard.tsx             # Main research page
│   └── ResultsDetail.tsx         # Single run details
├── hooks/
│   ├── useResearch.ts            # Fetch + polling logic
│   └── useLocalStorage.ts        # Session/history persistence
├── services/
│   ├── ariaClient.ts             # Typed API client with retry
│   └── types.ts                  # TypeScript interfaces from API
├── App.tsx
├── main.tsx
└── index.css
```

### Type Definitions
```typescript
// src/services/types.ts

export interface AgentOutput {
  findings: string[];
  confidence: number;
  sources: string[];
  raw_output: string;
}

export interface ResearchResult {
  request_id: string;
  status: 'queued' | 'running' | 'complete' | 'error';
  topic: string;
  progress?: number;
  results?: {
    advocate: AgentOutput;
    skeptic: AgentOutput;
    domain: AgentOutput;
    arbitrator: {
      synthesis: string;
      confidence_score: number;
      gaps_identified: string[];
      recommendation: string;
    };
  };
  created_at: string;
  completed_at?: string;
  error?: string;
}

export interface ResearchRun {
  request_id: string;
  topic: string;
  status: 'complete' | 'error';
  created_at: string;
}
```

### Component Props Example
```typescript
// AgentPanel.tsx
export interface AgentPanelProps {
  agentName: 'advocate' | 'skeptic' | 'domain';
  data: AgentOutput | null;
  isLoading: boolean;
  error?: string;
}

export const AgentPanel: React.FC<AgentPanelProps> = ({
  agentName,
  data,
  isLoading,
  error,
}) => {
  // Renders independently with mock data for testing
};
```

---

## 5. Frontend Features (Phase 1)

### Dashboard Page
- [ ] ResearchForm component (topic + query inputs)
- [ ] Submit button → POST /v1/research/start
- [ ] Show request_id and polling status
- [ ] Display 4 agent panels as they complete (via polling GET)
- [ ] Display arbitrator summary at bottom
- [ ] Error handling (network, timeout, backend errors)
- [ ] Loading skeleton states for each agent

### Results Detail Page
- [ ] Route: `/results/{request_id}`
- [ ] Fetch completed research run
- [ ] Display all agent findings side-by-side
- [ ] Display arbitrator synthesis
- [ ] Link sources (clickable URLs)
- [ ] Copy-to-clipboard for each finding

### Results History Page
- [ ] Fetch GET /v1/research?limit=10
- [ ] Display list of past runs
- [ ] Link to detail page
- [ ] Delete functionality (optional for Phase 1)

---

## 6. Styling Approach (Phase 1)

**Option A (Minimal):** Plain CSS + Tailwind basics
- Light background, dark text
- Agent panels: 2x2 grid (desktop) or stacked (mobile)
- Each agent has a color: Advocate=green, Skeptic=red, Domain=blue, Arbitrator=purple
- Card-based layout with shadows

**Option B (Advanced):** Tailwind + shadcn/ui components
- Toast notifications for errors
- Tabs or modals for agent details
- More polished UX

**Recommendation:** Start with Option A, upgrade to Option B in Phase 2.

---

## 7. Data Flow Diagram

```
User Input
    ↓
ResearchForm (topic, query)
    ↓
POST /v1/research/start → get request_id
    ↓
useResearch hook (polling GET /v1/research/{id})
    ↓
Status: queued → running (0-100%)
    ↓
Status: complete → parse results
    ↓
Render AgentPanel × 4 + ArbitratorSummary
    ↓
User views, saves via localStorage, navigates to past runs
```

---

## 8. Backend Implementation Phases

### Phase 1 (Foundation)
- [ ] LangGraph graph setup (4 agent nodes + router)
- [ ] Tavily integration (keyword, counter, domain searches)
- [ ] LLM integration (prompt engineering for each agent)
- [ ] FastAPI server with `/v1/research/start` and `/v1/research/{id}`
- [ ] In-memory or JSON file storage

### Phase 2 (Enhancement)
- [ ] WebSocket support for real-time updates (optional)
- [ ] Database (SQLite or Postgres)
- [ ] Caching of results
- [ ] Rate limiting
- [ ] Logging (Python logging module, not print())

---

## 9. Development Workflow

### For Frontend (Per Component)

**Step 1:** Create component file with **mock data** (no API calls yet)
```bash
# Example: AgentPanel.tsx with hardcoded props
npm run dev  # See component rendered perfectly
```

**Step 2:** Write tests
```bash
npm test AgentPanel
```

**Step 3:** Integrate API client (once backend is ready)
```typescript
// data comes from ariaClient, not mock
const [data, setData] = useState<AgentOutput | null>(null);
const { findings } = await ariaClient.getResearchResult(id);
setData(findings.advocate);
```

**Step 4:** Deploy and validate against real backend

### For Backend

**Step 1:** Lock API contract (this spec) ✅ Done
**Step 2:** Implement LangGraph agents
**Step 3:** Implement FastAPI routes matching contract
**Step 4:** Test with curl or Postman
**Step 5:** Deploy

---

## 10. Success Criteria

### Backend
- [ ] All 4 agents produce structured JSON output (never raw strings)
- [ ] /v1/research/{id} returns complete results in <3 minutes
- [ ] Tavily searches cover pro/counter/domain perspectives
- [ ] All API keys loaded from .env
- [ ] Logging via Python logging module (not print)

### Frontend
- [ ] All components render isolated (tests with mock data)
- [ ] Polling works without race conditions (useResearch hook)
- [ ] Error states displayed to user
- [ ] Works on desktop (mobile optional Phase 2)
- [ ] Type-safe: zero `any` types
- [ ] Conventional Commits: `feat()`, `fix()`, `docs()` messages

### Full Stack
- [ ] End-to-end flow: input → polling → results display
- [ ] <2sec response time from frontend form to first agent data
- [ ] Responsive design
- [ ] No console errors

---

## 11. Constraints & Rules

### Copilot/Developer Must Enforce
- ❌ Never use `print()` → use `logging` module
- ❌ Never hardcode API keys → use `.env`
- ❌ Never return raw LLM strings → always parse to JSON first
- ❌ Never collapse 4 agents into 1 prompt
- ❌ Never use `any` types in TypeScript → always explicit types
- ✅ Always include error handling (try/catch, client-side validation)
- ✅ Always write tests alongside code
- ✅ Always use Conventional Commits

---

## 12. Next Steps

1. **Backend Developer**: Implement LangGraph orchestration + API routes (should match this contract exactly)
2. **Frontend Developer (You)**: 
   - Start with Dashboard page stub
   - Create mock data (fake Tavily responses)
   - Build AgentPanel component in isolation
   - Write tests
   - Integrate ariaClient once backend endpoint exists

3. **Validation**: 
   - Run full end-to-end flow with sample data
   - Verify polling works under 200ms latency
   - Ensure error states display correctly

---

## 13. File Locations

- Backend repo: (TBD)
- Frontend repo: `/flipside2`
- This spec: `/flipside2/PROJECT_SPEC.md`
- Environment file: `/flipside2/.env` (not committed)
- Type definitions: `/flipside2/src/services/types.ts`

---

**Ready to implement. Frozen spec prevents rework. Build to this contract exactly.**
