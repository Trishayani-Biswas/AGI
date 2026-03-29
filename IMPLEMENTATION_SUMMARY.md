# FlipSide 2.0 - Complete Redesign

## Quick Start

Run these commands in your terminal:

```bash
cd "c:\Users\jitpa\OneDrive\Documents\JIT\PROJECTS\Formal\flipside2"
npm install
node setup-project.mjs
npm run dev
```

This will:
1. Install dependencies (Tailwind CSS, Framer Motion, Lucide, Recharts, etc.)
2. Create the complete modular architecture (~50 components)
3. Start the dev server at http://localhost:5173

## What's New in v2.0

### Design System
- **Black Gold Premium Theme** - Dark warm base with gold accents
- **Glass Surface Effects** - Backdrop blur with subtle borders
- **Framer Motion Animations** - Smooth page transitions, hover effects
- **Custom Typography** - Inter font with defined scale

### Architecture
- **Modular Components** - 50+ reusable components
- **Custom Hooks** - useDebate, useTimer, useToast, useLocalStorage
- **Type-Safe** - Full TypeScript with strict mode
- **Path Aliases** - Clean imports with @/

### Features
- **Setup Screen** - Topic input, mode selection, side picker, timer, multiplayer
- **Debate Screen** - Real-time chat, timer, scoring, AI coach
- **Stats Screen** - Verdict, score breakdown, charts, export

## File Structure

```
src/
├── types/index.ts          # TypeScript definitions
├── hooks/
│   ├── useDebate.ts        # Debate state management
│   ├── useTimer.ts         # Countdown timer
│   ├── useToast.ts         # Toast notifications
│   └── useLocalStorage.ts  # Persistent storage
├── lib/
│   ├── backendClient.ts    # API client + Anthropic
│   ├── storage.ts          # localStorage utils
│   ├── aiPrompts.ts        # AI system prompts
│   └── scoring.ts          # Score calculation
├── components/
│   ├── ui/                 # Base components
│   ├── setup/              # Setup screen components
│   ├── debate/             # Debate screen components
│   └── stats/              # Stats screen components
├── screens/
│   ├── SetupScreen.tsx
│   ├── DebateScreen.tsx
│   └── StatsScreen.tsx
├── FlipSideNew.tsx         # Main orchestrator
├── AppNew.tsx              # App entry
└── index.css               # Tailwind + custom styles
```

## To Use New Architecture

After running `setup-project.mjs`, update `src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './AppNew'  // Changed from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

## API Configuration

The app works in two modes:

### Mock Mode (Default)
- No API key required
- Uses intelligent mock responses
- Works completely offline

### Anthropic Claude Mode
- Set API key in localStorage: `flipside_api_key`
- Uses Claude claude-sonnet-4-20250514 model
- Real AI debate responses + coaching tips

## Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `background` | `#0A0804` | Main background |
| `surface` | `#12100A` | Card backgrounds |
| `surface-raised` | `#1C1810` | Elevated elements |
| `border` | `#2A2318` | Borders |
| `gold-primary` | `#D4A843` | Primary accent |
| `gold-muted` | `#A07C2A` | Secondary accent |
| `text-primary` | `#F5ECD7` | Main text |
| `text-secondary` | `#9E8E6F` | Muted text |

## Development

```bash
npm run dev       # Start dev server
npm run build     # Production build
npm run lint      # Run ESLint
npm run test      # Run tests
npm run preview   # Preview production build
```

## Backend (Optional)

```bash
npm run backend   # Start backend server on port 3001
```

Endpoints:
- `GET /health` - Health check
- `GET/POST /v1/history` - Sync debate history
- `POST /v1/multiplayer/rooms` - Create multiplayer room

---

**FlipSide 2.0 - Your AI Debate Partner** 🎯
