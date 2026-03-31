# How to Get the Best Frontend Work from Me

This guide explains how to request components, features, and changes to get the highest quality output with minimal rework.

---

## 1. The Golden Rule: Frozen Spec = Frozen Code

**Don't ask for vague features.** Instead:

### ❌ Bad Request
>
> "Build the dashboard page"

### ✅ Good Request
>
> "Build Dashboard page per PROJECT_SPEC.md, section 5.1:
>
> - ResearchForm with topic + query inputs
> - Submit button posts to /v1/research/start
> - Display returned request_id as a badge
> - Show polling status: queued → running → complete
> - On complete, render 4 AgentPanel components per the mocked response in tests/fixtures/research-complete.json
> - Include error boundary for network failures
> - Test with mock data first, no backend integration yet"

---

## 2. Component-First Workflow

### Phase: Isolation (Build with Mock Data)

**Request Format:**

```
Build {ComponentName} component:
- Props: {interface definition}
- Behavior: {user interactions}
- Test with: {fixture file path}
- Styling: {color scheme or reference}
- No backend integration yet
```

**Example:**

```
Build AgentPanel component:
- Props: AgentPanelProps per types.ts
- Behavior: Display findings list, sources as links, confidence score as progress bar
- Test with: tests/fixtures/agent-advocate.json
- Styling: Tailwind, agent color from agentName prop (advocate=green)
- No API calls yet — data comes from props only
```

**What I'll deliver:**

- ✅ Component file (AgentPanel.tsx)
- ✅ Component test file (AgentPanel.test.tsx with mock data)
- ✅ Can render in Storybook or dev mode with fake data
- ✅ All props typed, zero `any` types

### Phase: Integration (Connect to API)

**Request Format:**

```
Integrate {ComponentName} with API:
- Fetch endpoint: {GET/POST endpoint}
- Data transform: {how response maps to props}
- Error handling: {what to show on 500, timeout, etc}
- Loading state: {spinner? skeleton?}
```

**Example:**

```
Integrate Dashboard polling with ariaClient:
- Fetch endpoint: GET /v1/research/{request_id}
- Data transform: response.results → pass to AgentPanel props
- Polling: every 2 seconds until status !== 'running'
- Error handling: show toast on network error, retry button
- Loading state: show AgentPanel skeleton while fetching
```

**What I'll deliver:**

- ✅ useResearch hook (handles polling, retry, cancel)
- ✅ Dashboard component updated to use the hook
- ✅ Tests with mocked ariaClient responses
- ✅ Real error states tested

---

## 3. How to Request Features I'll Build Perfectly

### Type & Props First

**Always provide TypeScript interfaces before asking for a component:**

```typescript
// In PROJECT_SPEC.md or types.ts
interface AgentPanelProps {
  agentName: 'advocate' | 'skeptic' | 'domain';
  data: AgentOutput | null;
  isLoading: boolean;
  error?: string;
}
```

**Then request:**
> "Build AgentPanel per AgentPanelProps. Data comes via props (isolation phase). Tests use mock data from fixtures/agent-advocate.json."

### Mock Data Files

**Create fixture files for me to test against:**

```json
// tests/fixtures/agent-advocate.json
{
  "findings": [
    "Finding 1 supporting the topic",
    "Finding 2 with evidence"
  ],
  "confidence": 0.85,
  "sources": ["https://example.com/1", "https://example.com/2"],
  "raw_output": "Full agent response text..."
}
```

**Request:**
> "Build AgentPanel component. Test it with tests/fixtures/agent-advocate.json as the data prop. Wire up isLoading: false, error: undefined."

---

## 4. Layout & Visual Specs

### Grid/Layout Requests

**Provide explicit grid structure:**

```
Request: "Build Dashboard layout:
- Top: ResearchForm (full width)
- Middle: 2x2 grid of AgentPanel components (desktop)
- Mobile: stacked single column
- Bottom: ArbitratorSummary (full width)
- Gaps: 1.5rem between panels
- Padding: 2rem around container
- Max width: 1200px, centered"
```

### Color & Styling

**Specify agent colors explicitly:**

```
Styling:
- Advocate: bg-green-50 border-l-4 border-green-500
- Skeptic: bg-red-50 border-l-4 border-red-500
- Domain: bg-blue-50 border-l-4 border-blue-500
- Arbitrator: bg-purple-50 border-l-4 border-purple-500
- Text: gray-900 (dark mode: gray-50)
```

**Or send a screenshot/figma link and say:**
> "Match the design in [link]. Use Tailwind utilities. Responsive for mobile."

---

## 5. Testing Expectations

### What I'll Always Include

When you request a component, I'll deliver:

```typescript
// AgentPanel.test.tsx
import { render, screen } from '@testing-library/react';
import { AgentPanel } from './AgentPanel';
import mockData from '../fixtures/agent-advocate.json';

describe('AgentPanel', () => {
  it('renders findings list', () => {
    render(
      <AgentPanel
        agentName="advocate"
        data={mockData}
        isLoading={false}
      />
    );
    expect(screen.getByText('Finding 1 supporting the topic')).toBeInTheDocument();
  });

  it('shows loading spinner when isLoading=true', () => {
    render(
      <AgentPanel
        agentName="advocate"
        data={null}
        isLoading={true}
      />
    );
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('displays error message when error prop is set', () => {
    render(
      <AgentPanel
        agentName="advocate"
        data={null}
        isLoading={false}
        error="Failed to fetch"
      />
    );
    expect(screen.getByText('Failed to fetch')).toBeInTheDocument();
  });
});
```

**To run tests:**

```bash
npm run test -- AgentPanel
```

---

## 6. File Organization (To Request Correctly)

```
src/
├── components/
│   ├── AgentPanel.tsx          # "Build AgentPanel component"
│   ├── AgentPanel.test.tsx     # Included automatically
│   ├── ResearchForm.tsx        # "Build ResearchForm component"
│   ├── Dashboard.tsx           # "Build Dashboard page"
│   └── ...
├── pages/
│   ├── Dashboard.tsx
│   ├── ResultsDetail.tsx
│   └── ...
├── services/
│   ├── types.ts                # Type definitions (you update)
│   ├── ariaClient.ts           # "Build ariaClient with methods: getResearchStart(), getResearchResult()"
│   └── fixtures.ts             # Mock data helpers
├── hooks/
│   ├── useResearch.ts          # "Build useResearch hook for polling"
│   └── ...
└── App.tsx
```

**Request format:**

```
Build src/components/AgentPanel.tsx per types.AgentPanelProps
```

vs.

```
Build the AgentPanel component somewhere
```

---

## 7. Error & Loading States (Must Specify)

### What to specify upfront

```
Error States:
- Network timeout (>5s): "Request timed out. Retry?"
- 404 /v1/research/{id}: "Research run not found"
- 500: "Server error. Try again later"
- Malformed response: "Invalid response format"

Loading States:
- Initial: Show AgentPanel skeleton × 4
- Polling: Show "Fetching..." with loop counter
- On complete: Fade in real data

Retry Logic:
- On failure: Show "Retry" button
- Max 3 retries before surfacing error
```

---

## 8. Performance & UX Specs

### Request format

```
Build useResearch hook:
- Polling interval: 2000ms (configurable)
- Max attempts: 30 (before timeout)
- Abort signal: cleanup on unmount
- Dedupe: don't refetch if request_id hasn't changed
- Cancel: expose cancel() method
```

**Result:**

```typescript
// Dashboard.tsx
const { data, loading, error, cancel } = useResearch(requestId);

useEffect(() => {
  return cancel; // Cleanup on unmount
}, []);
```

---

## 9. Git Workflow (Commits I'll Make)

**When you say:** "Build AgentPanel component"

**I'll commit:**

```
feat(components): add AgentPanel with finding display

- Render agent findings with confidence score
- Style by agent type (color-coded border)
- Include error and loading states
- Add unit tests with mock data
```

**When integrating:** "Integrate AgentPanel with useResearch"

**I'll commit:**

```
feat(hooks): add useResearch polling hook

- Poll GET /v1/research/{id} until complete
- Handle timeout and network errors
- Expose cancel() for cleanup
- Add tests with mocked fetch
```

---

## 10. Requests That Lead to Rework (Avoid These)

### ❌ "Make it look nice"

**Better:** "Style per PROJECT_SPEC.md section 6 (agent colors, card layout, Tailwind only)"

### ❌ "Add dark mode support"

**Better:** "Add dark mode toggle in Header. Use CSS variables for both light/dark tokens. Update tailwind.config.ts with darkMode: 'class'."

### ❌ "Fix the frontend" (after backend changes)

**Better:** "Backend API changed: arbitrator now returns {score, gaps} instead of {synthesis, score}. Update types.ts, then update ArbitratorSummary component to match."

### ❌ "Make it work with the backend"

**Better:** "Backend endpoint is now live at <http://localhost:8000/v1/research>. Create ariaClient wrapper around fetch with retry logic. Update Dashboard to use POST /v1/research/start, then use useResearch hook for polling."

---

## 11. Request Template

**Copy and fill this out for maximum clarity:**

```markdown
# Build/Fix {ComponentName}

## Context
[What page/feature is this part of?]

## Spec
[Reference PROJECT_SPEC.md section X, or paste interface]

## Props/Interface
[Exact TypeScript interface, or link to types.ts]

## Behavior
[What happens on user interaction? What data flows in/out?]

## Styling
[Colors, layout, responsive breakpoints]

## Testing
[Mock data file path, test cases to cover]

## Integration (if applicable)
[API endpoint, data transform, error handling]

## Success Criteria
- [ ] Component renders with mock data
- [ ] Tests pass (npm test)
- [ ] Zero console errors
- [ ] Responsive on mobile (if applicable)
```

---

## 12. Example: Full Request

```markdown
# Build Dashboard Page

## Context
Main research entry point. User enters topic, submits, sees 4 agent results stream in via polling.

## Spec
PROJECT_SPEC.md section 5.1 (Dashboard Page)

## Layout
```

[ResearchForm - full width]
[2x2 AgentPanel grid (desktop) / stacked (mobile)]
[ArbitratorSummary - full width]

```

## Behavior
1. User fills topic + query in ResearchForm
2. Clicks "Start Research"
3. ResearchForm posts to /v1/research/start via ariaClient
4. Gets back { request_id, status: 'queued' }
5. Show request_id badge + "Queued..."
6. useResearch hook polls GET /v1/research/{id} every 2s
7. On progress: show "Running 25%..." spinner
8. On complete: render AgentPanel × 4 with real data
9. Scroll to ArbitratorSummary
10. Show "Copy findings" + "Save to history" buttons

## Props/Types
- ResearchForm: takes onSubmit callback (requestId: string) => void
- AgentPanel: per types.AgentPanelProps
- ArbitratorSummary: per types.ArbitratorOutput
- useResearch: returns { data, loading, error, cancel }

## Styling
- Container: max-w-4xl, mx-auto, py-8, px-4
- ResearchForm: border-2, rounded-lg, p-6, bg-white
- Grid: grid grid-cols-1 md:grid-cols-2 gap-6
- ArbitratorSummary: border-l-4 border-purple-500, mt-8

## Testing
- Mock data: tests/fixtures/research-complete.json
- Test with form submission → polling → results display
- Test error state (400 invalid topic, 500 server error)
- Test timeout after 30 reqs

## Success Criteria
- [ ] Form inputs match ResearchForm interface
- [ ] Polling starts on submit, stops on complete
- [ ] All 4 AgentPanels render with real data
- [ ] Error states display correctly
- [ ] Tests pass with mocked fetch + useResearch
- [ ] Responsive: desktop grid, mobile stacked
```

---

## Summary

**To get the best frontend work:**

1. ✅ Provide exact specs (not vague requests)
2. ✅ Lock interfaces in types.ts first
3. ✅ Provide mock data files for testing
4. ✅ Request one component at a time (isolation)
5. ✅ Specify error + loading states upfront
6. ✅ Use the request template above
7. ✅ Commit often (small, reviewable changes)
8. ✅ Test with mock data before backend integration

**Result:** Components built right the first time, zero rework, fast iteration.
