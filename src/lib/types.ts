export type DebateMode = 'casual' | 'balanced' | 'intense'

export type Side = 'for' | 'against'

export type MessageRole = 'user' | 'ai'

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: number
  roundNumber: number
}

export interface Round {
  number: number
  winner: 'user' | 'ai' | 'tie'
  userScore: number
  aiScore: number
  duration: number
}

export interface Verdict {
  winner: 'user' | 'ai' | 'tie'
  summary: string
  strengths: string[]
  weaknesses: string[]
  overallAnalysis: string
}

export interface DebateSession {
  id: string
  topic: string
  mode: DebateMode
  side: Side
  messages: Message[]
  rounds: Round[]
  totalUserScore: number
  totalAiScore: number
  createdAt: number
  completedAt?: number
  verdict?: Verdict
}

export interface Player {
  id: string
  name: string
  avatarInitial: string
}

export interface AppSettings {
  apiKey: string
  defaultMode: DebateMode
  defaultTimer: number
  coachEnabled: boolean
}

export interface ToastMessage {
  id: string
  type: 'success' | 'error' | 'info'
  message: string
  duration?: number
}

export interface CoachTip {
  id: string
  content: string
  category: 'structure' | 'evidence' | 'rebuttal' | 'clarity'
}

export type Screen = 'setup' | 'debate' | 'stats'

export interface DebateState {
  session: DebateSession | null
  currentRound: number
  isAiThinking: boolean
  timerActive: boolean
  timeRemaining: number
}
