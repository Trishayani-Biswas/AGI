import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './FlipSide.css'
import {
  checkBackendHealth,
  createBackendRoom,
  pullHistoryFromBackend,
  pushHistoryToBackend,
} from './lib/backendClient'

type Side = 'For' | 'Against'
type Difficulty = 'Beginner' | 'Intermediate' | 'Advanced'
type Screen = 'setup' | 'debate' | 'stats'
type Role = 'user' | 'assistant'
type AiMode = 'auto' | 'mock' | 'gemini'
type ResolvedAiMode = 'mock' | 'gemini'

type Message = {
  role: Role
  content: string
  forfeited?: boolean
}

type RoundScore = {
  userPoints: number
  aiPoints: number
  reason: string
  userArgStrength: number
  aiArgStrength: number
}

type CoachInsight = {
  round: number
  clarity: number
  evidence: number
  structure: number
  rebuttal: number
  tip: string
}

type Verdict = {
  winner: 'User' | 'AI'
  summary: string
  strengths: string[]
  weaknesses: string[]
  bestRound: number
  mvpArgument: string
}

type DebateHistoryEntry = {
  id: string
  date: string
  topic: string
  side: Side
  difficulty: Difficulty
  tags: string[]
  totalRounds: number
  userScore: number
  aiScore: number
  messages: Message[]
  roundScores: RoundScore[]
  verdict: Verdict
}

type AiTurn = {
  text: string
  score: RoundScore
  modeUsed: ResolvedAiMode
  fallbackNotice?: string
}

const TOPIC_CATEGORIES: Record<string, string[]> = {
  Technology: [
    'AI will eliminate more jobs than it creates',
    'Social media does more harm than good',
    'Privacy is more important than national security',
    'Tech companies are too powerful to regulate',
  ],
  Education: [
    'Should AI replace teachers?',
    'Gap year is better than rushing college',
    'Standardized tests should be abolished',
    'Online education is as effective as classroom learning',
  ],
  Society: [
    'Reservations should be based on income, not caste',
    'Universal Basic Income should be implemented',
    'Capital punishment should be abolished',
    'Voting should be mandatory',
  ],
  'Science & Future': [
    'Space exploration is a waste of money',
    'Gene editing in humans should be allowed',
    'Nuclear energy is the future of power',
    "Mars colonization is humanity's best bet for survival",
  ],
}

const DIFFICULTIES: Difficulty[] = ['Beginner', 'Intermediate', 'Advanced']
const ROUND_TIMES: Record<Difficulty, number> = {
  Beginner: 180,
  Intermediate: 120,
  Advanced: 90,
}

const HISTORY_KEY = 'FLIPSIDE_HISTORY_V2'
const API_KEY_STORAGE = 'FLIPSIDE_GEMINI_KEY'
const DEPLOYMENT_URL_STORAGE = 'FLIPSIDE_BACKEND_URL'
const SAFETY_LEVEL_STORAGE = 'FLIPSIDE_SAFETY_LEVEL'

const GEMINI_MODEL = 'gemini-2.0-flash'
const GEMINI_DEFAULT_KEY = import.meta.env.VITE_GEMINI_API_KEY || ''
const HISTORY_DISPLAY_LIMIT = 30

const clamp = (value: number, min: number, max: number): number => Math.max(min, Math.min(max, value))

const randomFrom = <T,>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)]
const buildRoomCode = (): string => Math.random().toString(36).slice(2, 8).toUpperCase()

const deriveTags = (topic: string, side: Side, difficulty: Difficulty): string[] => {
  const normalized = topic.toLowerCase()
  const categoryTag =
    Object.entries(TOPIC_CATEGORIES).find(([, topics]) => topics.some((candidate) => candidate.toLowerCase() === normalized))?.[0] ||
    'Custom'
  return [categoryTag, difficulty, side]
}

const parseScore = (text: string): RoundScore | null => {
  const match = text.match(/SCORE:(\{[^\n]+\})/)
  if (!match) return null
  try {
    const parsed = JSON.parse(match[1]) as Partial<RoundScore>
    return {
      userPoints: clamp(Number(parsed.userPoints ?? 0), 0, 10),
      aiPoints: clamp(Number(parsed.aiPoints ?? 0), 0, 10),
      reason: String(parsed.reason ?? 'Round judged.'),
      userArgStrength: clamp(Number(parsed.userArgStrength ?? parsed.userPoints ?? 0), 0, 10),
      aiArgStrength: clamp(Number(parsed.aiArgStrength ?? parsed.aiPoints ?? 0), 0, 10),
    }
  } catch {
    return null
  }
}

const cleanText = (text: string): string => text.replace(/\nSCORE:\{[^\n]+\}/g, '').trim()

const debateSystemPrompt = (topic: string, userSide: Side, difficulty: Difficulty): string => {
  const aiSide = userSide === 'For' ? 'Against' : 'For'
  const style = {
    Beginner: 'You are a gentle debater. Keep arguments simple in 2-3 sentences.',
    Intermediate: 'You are a firm debater. Use 1-2 supporting points in 3-4 sentences.',
    Advanced: 'You are a razor-sharp debater. Use logic, examples, and structure in 4-5 sentences.',
  }[difficulty]

  return [
    `You are debating: "${topic}".`,
    `You argue ${aiSide}. The user argues ${userSide}.`,
    style,
    'After every response output exactly on a new line:',
    'SCORE:{"userPoints":<0-10>,"aiPoints":<0-10>,"reason":"<one short sentence>","userArgStrength":<0-10>,"aiArgStrength":<0-10>}',
  ].join('\n')
}

const buildLocalScore = (userArgument: string, difficulty: Difficulty): RoundScore => {
  const words = userArgument.trim().split(/\s+/).filter(Boolean)
  const wordCount = words.length
  const hasEvidence = /(data|study|report|research|evidence|according)/i.test(userArgument)
  const hasStructure = /(first|second|third|therefore|however|finally|because)/i.test(userArgument)
  const hasExample = /(for example|for instance|consider|imagine)/i.test(userArgument)

  const base = difficulty === 'Beginner' ? 4 : difficulty === 'Intermediate' ? 5 : 6
  const verbosityBoost = clamp(Math.floor(wordCount / 20), 0, 2)
  const evidenceBoost = hasEvidence ? 1 : 0
  const structureBoost = hasStructure ? 1 : 0
  const exampleBoost = hasExample ? 1 : 0

  const userPoints = clamp(base + verbosityBoost + evidenceBoost + structureBoost + exampleBoost, 2, 10)
  const aiBase = difficulty === 'Advanced' ? 7 : difficulty === 'Intermediate' ? 6 : 5
  const aiSwing = randomFrom([-1, 0, 1, 1])
  const aiPoints = clamp(aiBase + aiSwing, 3, 10)

  return {
    userPoints,
    aiPoints,
    reason: userPoints >= aiPoints ? 'Your argument landed with better structure this round.' : 'AI used stronger counter framing this round.',
    userArgStrength: userPoints,
    aiArgStrength: aiPoints,
  }
}

const buildMockResponse = (
  topic: string,
  side: Side,
  difficulty: Difficulty,
  round: number,
  totalRounds: number,
  userArgument: string,
): AiTurn => {
  const aiSide = side === 'For' ? 'Against' : 'For'
  const score = buildLocalScore(userArgument, difficulty)

  const openers = [
    `I argue ${aiSide.toLowerCase()} on this point because your claim misses second-order effects.`,
    `Your position sounds confident, but the premise is fragile under policy constraints.`,
    `Even if your argument is appealing, it does not survive real-world implementation costs.`,
  ]
  const closers = [
    'Can you quantify the impact instead of only asserting intent?',
    'Show one concrete case where your side works better at scale.',
    'If your side is right, explain why comparable systems often fail in practice.',
  ]

  const nuance =
    difficulty === 'Advanced'
      ? 'At advanced level, burden of proof and causal chain both matter, not just moral framing.'
      : difficulty === 'Intermediate'
        ? 'Your argument needs one more concrete support point to be robust.'
        : 'Nice effort. Make it simpler and use one clear example next round.'

  const text = [
    `${randomFrom(openers)} Topic context: ${topic}.`,
    nuance,
    `${randomFrom(closers)} (Round ${round}/${totalRounds})`,
  ].join(' ')

  return {
    text,
    score,
    modeUsed: 'mock',
  }
}

const buildCoachInsight = (userArgument: string, round: number): CoachInsight => {
  const words = userArgument.trim().split(/\s+/).filter(Boolean)
  const sentences = userArgument.split(/[.!?]+/).filter((chunk) => chunk.trim().length > 0)
  const hasEvidence = /(data|study|report|research|evidence|according|stat|percent|source)/i.test(userArgument)
  const hasStructure = /(first|second|third|therefore|however|because|in conclusion|finally)/i.test(userArgument)
  const hasRebuttal = /(counter|rebut|your point|opponent|however|although|while)/i.test(userArgument)

  const clarity = clamp(Math.round((Math.min(words.length, 90) / 90) * 10), 1, 10)
  const evidence = hasEvidence ? 8 : clamp(Math.round(clarity * 0.7), 2, 7)
  const structure = hasStructure ? 8 : clamp(Math.round((sentences.length / 4) * 10), 2, 7)
  const rebuttal = hasRebuttal ? 8 : 5

  const tip = hasEvidence
    ? 'Great use of support. Next round, tighten your rebuttal into one sharp counter.'
    : 'Add one concrete stat, study, or real example to strengthen credibility.'

  return { round, clarity, evidence, structure, rebuttal, tip }
}

const callGemini = async (messages: Message[], system: string, apiKey: string): Promise<string> => {
  const key = apiKey.trim()
  if (!key) throw new Error('Gemini API key missing.')

  const payload = {
    systemInstruction: { parts: [{ text: system }] },
    contents: messages.map((msg) => ({
      role: msg.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: msg.content }],
    })),
    generationConfig: {
      temperature: 0.42,
      maxOutputTokens: 900,
    },
  }

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${key}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data?.error?.message || 'Gemini request failed')
  }

  const text: string =
    data?.candidates?.[0]?.content?.parts?.map((part: { text?: string }) => part.text || '').join('') || ''

  if (!text.trim()) {
    throw new Error('Gemini returned an empty response.')
  }

  return text
}

const buildLocalVerdict = (userScore: number, aiScore: number, rounds: RoundScore[], messages: Message[]): Verdict => {
  const winner: 'User' | 'AI' = userScore >= aiScore ? 'User' : 'AI'
  const bestRoundIndex = rounds.reduce((best, current, index, arr) => {
    if (!arr[best]) return index
    return current.userPoints > arr[best].userPoints ? index : best
  }, 0)

  const mvpArg =
    [...messages].reverse().find((message) => message.role === 'user' && !message.forfeited)?.content ||
    'Your opening statement.'

  const strengths = [
    'Maintained clear stance under pressure',
    'Used progressive argument structure',
  ]

  const weaknesses = [
    'Could cite more specific evidence',
    'Rebuttals can be sharper and shorter',
  ]

  const summary =
    winner === 'User'
      ? 'You edged the debate by sustaining stronger round-by-round arguments.'
      : 'AI won on consistency, but your argument quality improved across rounds.'

  return {
    winner,
    summary,
    strengths,
    weaknesses,
    bestRound: bestRoundIndex + 1,
    mvpArgument: mvpArg,
  }
}

const transcriptFromDebate = (entry: DebateHistoryEntry): string => {
  const lines = [
    'FLIPSIDE DEBATE TRANSCRIPT',
    '===========================================',
    `Date: ${new Date(entry.date).toLocaleString()}`,
    `Topic: ${entry.topic}`,
    `Your Side: ${entry.side}`,
    `Difficulty: ${entry.difficulty}`,
    `Rounds: ${entry.totalRounds}`,
    `Final Score: YOU ${entry.userScore} - AI ${entry.aiScore}`,
    `Winner: ${entry.verdict.winner}`,
    `Summary: ${entry.verdict.summary}`,
    '',
    'Round Scores',
    '-------------------------------------------',
    ...entry.roundScores.map((score, index) => `R${index + 1}: YOU ${score.userPoints} - AI ${score.aiPoints} (${score.reason})`),
    '',
    'Debate Messages',
    '-------------------------------------------',
    ...entry.messages.map((message) => `[${message.role.toUpperCase()}] ${message.content}`),
    '',
    `MVP Argument: ${entry.verdict.mvpArgument}`,
    `Strengths: ${entry.verdict.strengths.join('; ')}`,
    `Weaknesses: ${entry.verdict.weaknesses.join('; ')}`,
  ]

  return lines.join('\n')
}

const markdownFromDebate = (entry: DebateHistoryEntry): string => {
  const scores = entry.roundScores
    .map(
      (score, index) =>
        `- Round ${index + 1}: YOU ${score.userPoints} - AI ${score.aiPoints} | ${score.reason}`,
    )
    .join('\n')

  const messages = entry.messages
    .map((message) => `- **${message.role === 'user' ? 'YOU' : 'AI'}**: ${message.content.replace(/\n/g, ' ')}`)
    .join('\n')

  return [
    `# FlipSide Debate Transcript`,
    '',
    `- Date: ${new Date(entry.date).toLocaleString()}`,
    `- Topic: ${entry.topic}`,
    `- Side: ${entry.side}`,
    `- Difficulty: ${entry.difficulty}`,
    `- Tags: ${entry.tags.join(', ')}`,
    `- Final Score: YOU ${entry.userScore} - AI ${entry.aiScore}`,
    `- Winner: ${entry.verdict.winner}`,
    '',
    `## Verdict`,
    entry.verdict.summary,
    '',
    `## Round Scores`,
    scores,
    '',
    `## Debate Messages`,
    messages,
    '',
    `## MVP Argument`,
    entry.verdict.mvpArgument,
  ].join('\n')
}

const csvFromHistory = (entries: DebateHistoryEntry[]): string => {
  const header = ['id', 'date', 'topic', 'side', 'difficulty', 'tags', 'rounds', 'userScore', 'aiScore', 'winner']
  const rows = entries.map((entry) =>
    [
      entry.id,
      entry.date,
      `"${entry.topic.replace(/"/g, '""')}"`,
      entry.side,
      entry.difficulty,
      `"${entry.tags.join('|')}"`,
      entry.totalRounds,
      entry.userScore,
      entry.aiScore,
      entry.verdict.winner,
    ].join(','),
  )
  return [header.join(','), ...rows].join('\n')
}

const downloadTextFile = (filename: string, text: string): void => {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

const readHistory = (): DebateHistoryEntry[] => {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as Array<DebateHistoryEntry & { tags?: string[] }>
    if (!Array.isArray(parsed)) return []
    return parsed.map((entry) => ({
      ...entry,
      tags: Array.isArray(entry.tags) && entry.tags.length ? entry.tags : deriveTags(entry.topic, entry.side, entry.difficulty),
    }))
  } catch {
    return []
  }
}

export default function FlipSide() {
  const [screen, setScreen] = useState<Screen>('setup')
  const [activeCategory, setActiveCategory] = useState('Technology')
  const [topic, setTopic] = useState('')
  const [customTopic, setCustomTopic] = useState('')
  const [side, setSide] = useState<Side>('For')
  const [difficulty, setDifficulty] = useState<Difficulty>('Intermediate')
  const [totalRounds, setTotalRounds] = useState(6)

  const [aiMode, setAiMode] = useState<AiMode>('auto')
  const [apiKey, setApiKey] = useState(() => localStorage.getItem(API_KEY_STORAGE) || GEMINI_DEFAULT_KEY || '')
  const [backendUrl, setBackendUrl] = useState(() => localStorage.getItem(DEPLOYMENT_URL_STORAGE) || '')
  const [safetyLevel, setSafetyLevel] = useState<'standard' | 'strict'>(() => {
    const saved = localStorage.getItem(SAFETY_LEVEL_STORAGE)
    return saved === 'strict' ? 'strict' : 'standard'
  })
  const [multiplayerEnabled, setMultiplayerEnabled] = useState(false)
  const [tournamentMode, setTournamentMode] = useState(false)
  const [roomCode, setRoomCode] = useState('')
  const [blockedCount, setBlockedCount] = useState(0)

  const [messages, setMessages] = useState<Message[]>([])
  const [roundScores, setRoundScores] = useState<RoundScore[]>([])
  const [coachInsights, setCoachInsights] = useState<CoachInsight[]>([])
  const [coachEnabled, setCoachEnabled] = useState(true)
  const [round, setRound] = useState(0)
  const [userScore, setUserScore] = useState(0)
  const [aiScore, setAiScore] = useState(0)
  const [timeLeft, setTimeLeft] = useState(0)
  const [timerActive, setTimerActive] = useState(false)
  const [loading, setLoading] = useState(false)
  const [verdict, setVerdict] = useState<Verdict | null>(null)
  const [history, setHistory] = useState<DebateHistoryEntry[]>(() => readHistory())
  const [historyQuery, setHistoryQuery] = useState('')
  const [historyDifficultyFilter, setHistoryDifficultyFilter] = useState<'All' | Difficulty>('All')
  const [historyWinnerFilter, setHistoryWinnerFilter] = useState<'All' | Verdict['winner']>('All')
  const [historyTagFilter, setHistoryTagFilter] = useState<'All' | string>('All')
  const [copied, setCopied] = useState(false)
  const [engineNotice, setEngineNotice] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [syncStatus, setSyncStatus] = useState<'idle' | 'ok' | 'error'>('idle')

  const inputRef = useRef<HTMLInputElement | null>(null)
  const timerRef = useRef<number | null>(null)
  const chatEndRef = useRef<HTMLDivElement | null>(null)

  const activeTopic = (topic || customTopic).trim()
  const roundTime = ROUND_TIMES[difficulty]

  const resolvedMode: ResolvedAiMode = useMemo(() => {
    if (aiMode === 'mock') return 'mock'
    if (aiMode === 'gemini') return apiKey.trim() ? 'gemini' : 'mock'
    return apiKey.trim() ? 'gemini' : 'mock'
  }, [aiMode, apiKey])

  const scorePct = Math.round((userScore / Math.max(userScore + aiScore, 1)) * 100)

  useEffect(() => {
    localStorage.setItem(API_KEY_STORAGE, apiKey)
  }, [apiKey])

  useEffect(() => {
    localStorage.setItem(DEPLOYMENT_URL_STORAGE, backendUrl)
  }, [backendUrl])

  useEffect(() => {
    localStorage.setItem(SAFETY_LEVEL_STORAGE, safetyLevel)
  }, [safetyLevel])

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history))
  }, [history])

  useEffect(() => {
    const handlePointerMove = (event: MouseEvent) => {
      document.documentElement.style.setProperty('--pointer-x', `${event.clientX}px`)
      document.documentElement.style.setProperty('--pointer-y', `${event.clientY}px`)
    }

    window.addEventListener('mousemove', handlePointerMove)
    return () => window.removeEventListener('mousemove', handlePointerMove)
  }, [])

  useEffect(() => {
    const selector = '.fs-btn, .fs-pill, .fs-topic'

    const resetMagnet = (element: HTMLElement) => {
      element.style.setProperty('--mag-x', '0px')
      element.style.setProperty('--mag-y', '0px')
      element.style.setProperty('--mag-rot-x', '0deg')
      element.style.setProperty('--mag-rot-y', '0deg')
    }

    const handleMouseMove = (event: MouseEvent) => {
      const target = (event.target as HTMLElement | null)?.closest(selector) as HTMLElement | null
      if (!target || target.matches(':disabled')) return

      const rect = target.getBoundingClientRect()
      const nx = (event.clientX - rect.left) / Math.max(rect.width, 1) - 0.5
      const ny = (event.clientY - rect.top) / Math.max(rect.height, 1) - 0.5

      target.style.setProperty('--mag-x', `${(nx * 8).toFixed(2)}px`)
      target.style.setProperty('--mag-y', `${(ny * 6).toFixed(2)}px`)
      target.style.setProperty('--mag-rot-x', `${(-ny * 5).toFixed(2)}deg`)
      target.style.setProperty('--mag-rot-y', `${(nx * 5).toFixed(2)}deg`)
    }

    const handleMouseOut = (event: MouseEvent) => {
      const fromElement = event.target as HTMLElement | null
      const toElement = event.relatedTarget as HTMLElement | null

      const source = fromElement?.closest(selector) as HTMLElement | null
      if (!source) return

      if (toElement && source.contains(toElement)) return
      resetMagnet(source)
    }

    const handleClick = (event: MouseEvent) => {
      const target = (event.target as HTMLElement | null)?.closest(selector) as HTMLElement | null
      if (!target || target.matches(':disabled')) return

      const rect = target.getBoundingClientRect()
      target.style.setProperty('--ripple-x', `${event.clientX - rect.left}px`)
      target.style.setProperty('--ripple-y', `${event.clientY - rect.top}px`)
      target.classList.remove('is-rippling')
      void target.offsetWidth
      target.classList.add('is-rippling')
      window.setTimeout(() => target.classList.remove('is-rippling'), 560)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseout', handleMouseOut)
    document.addEventListener('click', handleClick)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseout', handleMouseOut)
      document.removeEventListener('click', handleClick)
    }
  }, [])

  const stopTimer = useCallback(() => {
    setTimerActive(false)
    if (timerRef.current) window.clearTimeout(timerRef.current)
  }, [])

  const startTimer = useCallback(() => {
    setTimeLeft(roundTime)
    setTimerActive(true)
  }, [roundTime])

  const scrollToBottom = useCallback(() => {
    setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 60)
  }, [])

  const createHistoryEntry = useCallback(
    (finalMessages: Message[], finalScores: RoundScore[], finalUser: number, finalAi: number, finalVerdict: Verdict): DebateHistoryEntry => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      date: new Date().toISOString(),
      topic: activeTopic,
      side,
      difficulty,
      tags: deriveTags(activeTopic, side, difficulty),
      totalRounds,
      userScore: finalUser,
      aiScore: finalAi,
      messages: finalMessages,
      roundScores: finalScores,
      verdict: finalVerdict,
    }),
    [activeTopic, side, difficulty, totalRounds],
  )

  const finalizeDebate = useCallback(
    async (finalMessages: Message[], finalScores: RoundScore[], finalUser: number, finalAi: number) => {
      stopTimer()

      let finalVerdict: Verdict | null = null
      if (resolvedMode === 'gemini' && apiKey.trim()) {
        try {
          const summaryPrompt = [
            `You judged a full debate on "${activeTopic}". User side: ${side}.`,
            'Respond ONLY with valid JSON (no markdown):',
            '{"winner":"User" or "AI","summary":"one sentence","strengths":["s1","s2"],"weaknesses":["w1","w2"],"bestRound":1,"mvpArgument":"best user argument"}',
          ].join('\n')

          const raw = await callGemini(finalMessages, summaryPrompt, apiKey)
          finalVerdict = JSON.parse(raw.replace(/```json|```/g, '').trim()) as Verdict
        } catch {
          finalVerdict = null
        }
      }

      if (!finalVerdict) {
        finalVerdict = buildLocalVerdict(finalUser, finalAi, finalScores, finalMessages)
      }

      setVerdict(finalVerdict)
      setScreen('stats')

      const entry = createHistoryEntry(finalMessages, finalScores, finalUser, finalAi, finalVerdict)
      setHistory((prev) => [entry, ...prev].slice(0, HISTORY_DISPLAY_LIMIT))
    },
    [stopTimer, resolvedMode, apiKey, activeTopic, side, createHistoryEntry],
  )

  const generateAiTurn = useCallback(
    async (draftMessages: Message[], nextRound: number, userArgument: string): Promise<AiTurn> => {
      if (resolvedMode === 'mock') {
        await new Promise((resolve) => setTimeout(resolve, 550))
        return buildMockResponse(activeTopic, side, difficulty, nextRound, totalRounds, userArgument)
      }

      try {
        const raw = await callGemini(draftMessages, debateSystemPrompt(activeTopic, side, difficulty), apiKey)
        const parsed = parseScore(raw)
        const score = parsed ?? buildLocalScore(userArgument, difficulty)

        return {
          text: cleanText(raw),
          score,
          modeUsed: 'gemini',
        }
      } catch {
        const fallback = buildMockResponse(activeTopic, side, difficulty, nextRound, totalRounds, userArgument)
        return {
          ...fallback,
          fallbackNotice: 'Gemini unavailable, switched to Mock AI for this round.',
        }
      }
    },
    [resolvedMode, activeTopic, side, difficulty, totalRounds, apiKey],
  )

  const sendMessage = useCallback(async () => {
    const text = (inputRef.current?.value || '').trim()
    if (!text || loading || !activeTopic) return

    const unsafePattern = /(kill|suicide|self-harm|hate|terror|abuse)/i
    if (safetyLevel === 'strict' && unsafePattern.test(text)) {
      setEngineNotice('Strict safety mode blocked this message. Please rephrase with neutral and respectful language.')
      setBlockedCount((prev) => prev + 1)
      return
    }

    if (inputRef.current) inputRef.current.value = ''

    stopTimer()
    setLoading(true)
    setEngineNotice('')

    const userMessage: Message = { role: 'user', content: text }
    const nextRound = round + 1
    const withUser = [...messages, userMessage]

    setMessages(withUser)
    setRound(nextRound)

    try {
      const aiTurn = await generateAiTurn(withUser, nextRound, text)
      const assistantMessage: Message = {
        role: 'assistant',
        content: aiTurn.fallbackNotice ? `${aiTurn.text}\n\n[${aiTurn.fallbackNotice}]` : aiTurn.text,
      }

      const newMessages = [...withUser, assistantMessage]
      const newScores = [...roundScores, aiTurn.score]
      const newUser = userScore + aiTurn.score.userPoints
      const newAi = aiScore + aiTurn.score.aiPoints

      setMessages(newMessages)
      setRoundScores(newScores)
      setCoachInsights((prev) => [...prev, buildCoachInsight(text, nextRound)])
      setUserScore(newUser)
      setAiScore(newAi)
      setEngineNotice(aiTurn.modeUsed === 'mock' ? 'Running in Mock AI mode (no API required).' : 'Running in Gemini mode.')
      scrollToBottom()

      if (nextRound >= totalRounds) {
        await finalizeDebate(newMessages, newScores, newUser, newAi)
      } else {
        startTimer()
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unexpected error while generating response.'
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${message}` }])
    } finally {
      setLoading(false)
    }
  }, [
    loading,
    activeTopic,
    safetyLevel,
    stopTimer,
    round,
    messages,
    generateAiTurn,
    roundScores,
    userScore,
    aiScore,
    totalRounds,
    finalizeDebate,
    startTimer,
    scrollToBottom,
  ])

  const handleForfeit = useCallback(async () => {
    if (loading || !activeTopic) return

    stopTimer()
    const nextRound = round + 1
    const forfeitMessage: Message = {
      role: 'user',
      content: "Time's up - argument forfeited.",
      forfeited: true,
    }

    const penalty: RoundScore = {
      userPoints: 0,
      aiPoints: 3,
      reason: 'Round forfeited due to timer expiration.',
      userArgStrength: 0,
      aiArgStrength: 5,
    }

    const autoResponse: Message = {
      role: 'assistant',
      content: 'You forfeited this round on time. I take the point by default. Ready for the next one?',
    }

    const newMessages = [...messages, forfeitMessage, autoResponse]
    const newScores = [...roundScores, penalty]
    const newUser = userScore
    const newAi = aiScore + penalty.aiPoints

    setMessages(newMessages)
    setRound(nextRound)
    setRoundScores(newScores)
    setAiScore(newAi)
    scrollToBottom()

    if (nextRound >= totalRounds) {
      await finalizeDebate(newMessages, newScores, newUser, newAi)
    } else {
      startTimer()
    }
  }, [
    loading,
    activeTopic,
    stopTimer,
    round,
    messages,
    roundScores,
    userScore,
    aiScore,
    scrollToBottom,
    totalRounds,
    finalizeDebate,
    startTimer,
  ])

  useEffect(() => {
    if (!timerActive) return
    if (timeLeft <= 0) {
      void handleForfeit()
      return
    }
    timerRef.current = window.setTimeout(() => setTimeLeft((prev) => prev - 1), 1000)
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current)
    }
  }, [timerActive, timeLeft, handleForfeit])

  const startDebate = useCallback(() => {
    if (!activeTopic) return
    setMessages([])
    setRoundScores([])
    setCoachInsights([])
    setRound(0)
    setUserScore(0)
    setAiScore(0)
    setVerdict(null)
    setEngineNotice('')
    setScreen('debate')
    startTimer()
  }, [activeTopic, startTimer])

  const reset = useCallback(() => {
    stopTimer()
    setScreen('setup')
    setMessages([])
    setRoundScores([])
    setCoachInsights([])
    setRound(0)
    setUserScore(0)
    setAiScore(0)
    setVerdict(null)
    setEngineNotice('')
  }, [stopTimer])

  const backendBaseUrl = backendUrl.trim().replace(/\/+$/, '')

  const syncHistoryToBackend = useCallback(async () => {
    if (!backendBaseUrl) {
      setSyncStatus('error')
      setEngineNotice('Set a backend URL first to sync history.')
      return
    }

    setSyncing(true)
    try {
      await checkBackendHealth(backendBaseUrl)
      const saved = await pushHistoryToBackend(backendBaseUrl, history)
      setSyncStatus('ok')
      setEngineNotice(`Synced ${saved} debate entries to backend.`)
    } catch (error) {
      setSyncStatus('error')
      const message = error instanceof Error ? error.message : 'Failed to sync history.'
      setEngineNotice(`Backend sync failed: ${message}`)
    } finally {
      setSyncing(false)
    }
  }, [backendBaseUrl, history])

  const importHistoryFromBackend = useCallback(async () => {
    if (!backendBaseUrl) {
      setSyncStatus('error')
      setEngineNotice('Set a backend URL first to import history.')
      return
    }

    setSyncing(true)
    try {
      await checkBackendHealth(backendBaseUrl)
      const remote = await pullHistoryFromBackend<DebateHistoryEntry>(backendBaseUrl)
      if (!remote.length) {
        setSyncStatus('ok')
        setEngineNotice('Backend has no saved debates yet.')
        return
      }

      const merged = [...remote, ...history]
      const deduped = merged.reduce<DebateHistoryEntry[]>((acc, entry) => {
        if (!acc.some((item) => item.id === entry.id)) acc.push(entry)
        return acc
      }, [])
      setHistory(deduped.slice(0, HISTORY_DISPLAY_LIMIT))
      setSyncStatus('ok')
      setEngineNotice(`Imported ${remote.length} debate entries from backend.`)
    } catch (error) {
      setSyncStatus('error')
      const message = error instanceof Error ? error.message : 'Failed to import history.'
      setEngineNotice(`Backend import failed: ${message}`)
    } finally {
      setSyncing(false)
    }
  }, [backendBaseUrl, history])

  const handleCreateRoom = useCallback(async () => {
    if (!multiplayerEnabled) return
    if (!backendBaseUrl) {
      setRoomCode(buildRoomCode())
      setEngineNotice('Created local room code. Add backend URL for shared rooms.')
      return
    }

    setSyncing(true)
    try {
      await checkBackendHealth(backendBaseUrl)
      const created = await createBackendRoom(backendBaseUrl, activeTopic, 'local-user')
      setRoomCode(created)
      setSyncStatus('ok')
      setEngineNotice('Created multiplayer room via backend API.')
    } catch (error) {
      setSyncStatus('error')
      const message = error instanceof Error ? error.message : 'Failed to create room via backend.'
      setEngineNotice(`Room creation failed: ${message}`)
    } finally {
      setSyncing(false)
    }
  }, [multiplayerEnabled, backendBaseUrl, activeTopic])

  const exportCurrentTranscript = useCallback(async () => {
    if (!verdict || !activeTopic) return

    const tempEntry: DebateHistoryEntry = {
      id: 'live',
      date: new Date().toISOString(),
      topic: activeTopic,
      side,
      difficulty,
      tags: deriveTags(activeTopic, side, difficulty),
      totalRounds,
      userScore,
      aiScore,
      messages,
      roundScores,
      verdict,
    }

    const text = transcriptFromDebate(tempEntry)
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }, [verdict, activeTopic, side, difficulty, totalRounds, userScore, aiScore, messages, roundScores])

  const downloadCurrentTranscript = useCallback(() => {
    if (!verdict || !activeTopic) return

    const tempEntry: DebateHistoryEntry = {
      id: 'live',
      date: new Date().toISOString(),
      topic: activeTopic,
      side,
      difficulty,
      tags: deriveTags(activeTopic, side, difficulty),
      totalRounds,
      userScore,
      aiScore,
      messages,
      roundScores,
      verdict,
    }

    const safeTopic = activeTopic.replace(/[^a-zA-Z0-9-]+/g, '-').toLowerCase()
    downloadTextFile(`flipside-${safeTopic || 'debate'}.txt`, transcriptFromDebate(tempEntry))
  }, [verdict, activeTopic, side, difficulty, totalRounds, userScore, aiScore, messages, roundScores])

  const previewHistoryEntry = useCallback((entry: DebateHistoryEntry) => {
    setTopic(entry.topic)
    setCustomTopic('')
    setSide(entry.side)
    setDifficulty(entry.difficulty)
    setTotalRounds(entry.totalRounds)
    setMessages(entry.messages)
    setRoundScores(entry.roundScores)
    setUserScore(entry.userScore)
    setAiScore(entry.aiScore)
    setVerdict(entry.verdict)
    setRound(entry.totalRounds)
    setScreen('stats')
    setEngineNotice('Loaded from local history.')
  }, [])

  const allHistoryTags = useMemo(
    () => Array.from(new Set(history.flatMap((entry) => entry.tags))).sort((a, b) => a.localeCompare(b)),
    [history],
  )

  const filteredHistory = useMemo(() => {
    const query = historyQuery.trim().toLowerCase()
    return history.filter((entry) => {
      const queryMatch =
        !query ||
        entry.topic.toLowerCase().includes(query) ||
        entry.tags.some((tag) => tag.toLowerCase().includes(query)) ||
        entry.verdict.summary.toLowerCase().includes(query)

      const difficultyMatch = historyDifficultyFilter === 'All' || entry.difficulty === historyDifficultyFilter
      const winnerMatch = historyWinnerFilter === 'All' || entry.verdict.winner === historyWinnerFilter
      const tagMatch = historyTagFilter === 'All' || entry.tags.includes(historyTagFilter)

      return queryMatch && difficultyMatch && winnerMatch && tagMatch
    })
  }, [history, historyQuery, historyDifficultyFilter, historyWinnerFilter, historyTagFilter])

  const historyAnalytics = useMemo(() => {
    const total = history.length
    const userWins = history.filter((entry) => entry.verdict.winner === 'User').length
    const avgUser =
      total === 0 ? 0 : Math.round((history.reduce((sum, entry) => sum + entry.userScore, 0) / total) * 10) / 10
    const avgAi = total === 0 ? 0 : Math.round((history.reduce((sum, entry) => sum + entry.aiScore, 0) / total) * 10) / 10
    const tagCounts = history.flatMap((entry) => entry.tags).reduce<Record<string, number>>((acc, tag) => {
      acc[tag] = (acc[tag] || 0) + 1
      return acc
    }, {})
    const topTag = Object.entries(tagCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'

    return {
      total,
      userWins,
      winRate: total === 0 ? 0 : Math.round((userWins / total) * 100),
      avgUser,
      avgAi,
      topTag,
    }
  }, [history])

  const avgUser = roundScores.length
    ? Math.round((roundScores.reduce((sum, item) => sum + item.userPoints, 0) / roundScores.length) * 10) / 10
    : 0
  const avgAi = roundScores.length
    ? Math.round((roundScores.reduce((sum, item) => sum + item.aiPoints, 0) / roundScores.length) * 10) / 10
    : 0
  const coachAverages = coachInsights.length
    ? {
        clarity: Math.round((coachInsights.reduce((sum, item) => sum + item.clarity, 0) / coachInsights.length) * 10) / 10,
        evidence: Math.round((coachInsights.reduce((sum, item) => sum + item.evidence, 0) / coachInsights.length) * 10) / 10,
        structure: Math.round((coachInsights.reduce((sum, item) => sum + item.structure, 0) / coachInsights.length) * 10) / 10,
        rebuttal: Math.round((coachInsights.reduce((sum, item) => sum + item.rebuttal, 0) / coachInsights.length) * 10) / 10,
      }
    : { clarity: 0, evidence: 0, structure: 0, rebuttal: 0 }

  if (screen === 'setup') {
    return (
      <div className="fs-page fs-bg-animated">
        <div className="fs-floating fs-floating-1" />
        <div className="fs-floating fs-floating-2" />

        <div className="fs-shell">
          <header className="fs-header-card fs-pop-in">
            <div>
              <p className="fs-eyebrow">AI Debate Arena</p>
              <h1 className="fs-title">
                Flip<span>Side</span>
              </h1>
              <p className="fs-subtitle">Debate prototype with animated UI, local history, and zero-API mock mode.</p>
            </div>
            <div className="fs-chip-row">
              <span className="fs-chip">No API needed now</span>
              <span className="fs-chip">Gemini ready later</span>
              <span className="fs-chip">History persisted</span>
            </div>
          </header>

          <section className="fs-grid fs-pop-in fs-delay-1">
            <div className="fs-card">
              <h3>Debate Setup</h3>

              <label className="fs-label">Topic Category</label>
              <div className="fs-pill-wrap">
                {Object.keys(TOPIC_CATEGORIES).map((category) => (
                  <button
                    key={category}
                    type="button"
                    className={`fs-pill ${activeCategory === category ? 'is-active' : ''}`}
                    onClick={() => setActiveCategory(category)}
                  >
                    {category}
                  </button>
                ))}
              </div>

              <label className="fs-label">Pick Topic</label>
              <div className="fs-topic-list">
                {TOPIC_CATEGORIES[activeCategory].map((entry) => (
                  <button
                    key={entry}
                    type="button"
                    className={`fs-topic ${topic === entry ? 'is-active' : ''}`}
                    onClick={() => {
                      setTopic(entry)
                      setCustomTopic('')
                    }}
                  >
                    {entry}
                  </button>
                ))}
              </div>

              <input
                value={customTopic}
                onChange={(event) => {
                  setCustomTopic(event.target.value)
                  setTopic('')
                }}
                className="fs-input"
                placeholder="Or type your own topic..."
                aria-label="Custom debate topic"
              />

              <div className="fs-form-grid">
                <div>
                  <label className="fs-label">Your Side</label>
                  <div className="fs-pill-wrap">
                    {(['For', 'Against'] as Side[]).map((entry) => (
                      <button
                        key={entry}
                        type="button"
                        className={`fs-pill ${side === entry ? 'is-active' : ''}`}
                        onClick={() => setSide(entry)}
                      >
                        {entry}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="fs-label">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(event) => setDifficulty(event.target.value as Difficulty)}
                    className="fs-input"
                    aria-label="Select debate difficulty"
                    title="Select debate difficulty"
                  >
                    {DIFFICULTIES.map((entry) => (
                      <option key={entry} value={entry}>
                        {entry} ({ROUND_TIMES[entry]}s/round)
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="fs-label">Rounds</label>
                  <select
                    value={totalRounds}
                    onChange={(event) => setTotalRounds(Number(event.target.value))}
                    className="fs-input"
                    aria-label="Select number of rounds"
                    title="Select number of rounds"
                  >
                    {[4, 6, 8, 10].map((entry) => (
                      <option key={entry} value={entry}>
                        {entry}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="fs-mode-block">
                <label className="fs-label">AI Mode</label>
                <div className="fs-pill-wrap">
                  {(['auto', 'mock', 'gemini'] as AiMode[]).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      className={`fs-pill ${aiMode === mode ? 'is-active' : ''}`}
                      onClick={() => setAiMode(mode)}
                    >
                      {mode === 'auto' ? 'Auto' : mode === 'mock' ? 'Mock (No API)' : 'Gemini'}
                    </button>
                  ))}
                </div>
                <p className="fs-note">Current engine: {resolvedMode === 'mock' ? 'Mock AI (offline-friendly)' : 'Gemini API'}</p>
              </div>

              <div className="fs-mode-block">
                <label className="fs-label">Debate Coach</label>
                <div className="fs-pill-wrap">
                  <button
                    type="button"
                    className={`fs-pill ${coachEnabled ? 'is-active' : ''}`}
                    onClick={() => setCoachEnabled(true)}
                  >
                    Enabled
                  </button>
                  <button
                    type="button"
                    className={`fs-pill ${!coachEnabled ? 'is-active' : ''}`}
                    onClick={() => setCoachEnabled(false)}
                  >
                    Disabled
                  </button>
                </div>
                <p className="fs-note">Provides per-round writing and strategy feedback.</p>
              </div>

              <div className="fs-mode-block">
                <label className="fs-label">Safety Level</label>
                <div className="fs-pill-wrap">
                  <button
                    type="button"
                    className={`fs-pill ${safetyLevel === 'standard' ? 'is-active' : ''}`}
                    onClick={() => setSafetyLevel('standard')}
                  >
                    Standard
                  </button>
                  <button
                    type="button"
                    className={`fs-pill ${safetyLevel === 'strict' ? 'is-active' : ''}`}
                    onClick={() => setSafetyLevel('strict')}
                  >
                    Strict
                  </button>
                </div>
                <p className="fs-note">Blocked messages this session: {blockedCount}</p>
              </div>

              <div className="fs-mode-block">
                <label className="fs-label">Multiplayer (Beta)</label>
                <div className="fs-pill-wrap">
                  <button
                    type="button"
                    className={`fs-pill ${multiplayerEnabled ? 'is-active' : ''}`}
                    onClick={() => setMultiplayerEnabled(true)}
                  >
                    Enabled
                  </button>
                  <button
                    type="button"
                    className={`fs-pill ${!multiplayerEnabled ? 'is-active' : ''}`}
                    onClick={() => {
                      setMultiplayerEnabled(false)
                      setRoomCode('')
                    }}
                  >
                    Disabled
                  </button>
                </div>
                {multiplayerEnabled && (
                  <div className="fs-history-actions">
                    <button type="button" className="fs-btn fs-btn-small" onClick={() => void handleCreateRoom()} disabled={syncing}>
                      Create Room
                    </button>
                    <button
                      type="button"
                      className="fs-btn fs-btn-small"
                      onClick={() =>
                        setEngineNotice(
                          backendBaseUrl
                            ? `Use ${backendBaseUrl}/v1/multiplayer to wire join flow in your backend app.`
                            : 'Add backend URL to enable real multiplayer join.',
                        )
                      }
                    >
                      Join via Backend
                    </button>
                  </div>
                )}
                {roomCode && <p className="fs-note">Room Code: {roomCode}</p>}
              </div>

              <div className="fs-mode-block">
                <label className="fs-label">Tournament Mode</label>
                <div className="fs-pill-wrap">
                  <button
                    type="button"
                    className={`fs-pill ${tournamentMode ? 'is-active' : ''}`}
                    onClick={() => setTournamentMode(true)}
                  >
                    Enabled
                  </button>
                  <button
                    type="button"
                    className={`fs-pill ${!tournamentMode ? 'is-active' : ''}`}
                    onClick={() => setTournamentMode(false)}
                  >
                    Disabled
                  </button>
                </div>
                <p className="fs-note">When enabled, each completed debate counts as one bracket match.</p>
              </div>

              <label className="fs-label">Gemini API Key (optional now)</label>
              <input
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                className="fs-input"
                placeholder="AIza..."
                aria-label="Gemini API key"
              />

              <label className="fs-label">Future Backend URL (optional)</label>
              <input
                value={backendUrl}
                onChange={(event) => setBackendUrl(event.target.value)}
                className="fs-input"
                placeholder="https://api.yourdomain.com"
                aria-label="Future backend URL"
              />
              <p className="fs-note">Used later for account sync, webhooks, and multiplayer APIs.</p>
              {backendUrl.trim() && (
                <p className="fs-note">
                  API scaffolding ready: `{backendUrl.replace(/\/+$/, '')}/v1/history`, `/v1/multiplayer`, `/v1/webhooks`
                </p>
              )}
              <p className="fs-note">
                Sync status: {syncStatus === 'ok' ? 'Connected' : syncStatus === 'error' ? 'Error' : 'Idle'}
              </p>

              <button type="button" className="fs-btn fs-btn-primary" onClick={startDebate} disabled={!activeTopic}>
                Start Debate
              </button>
            </div>

            <div className="fs-card">
              <div className="fs-history-head">
                <h3 className="fs-history-title">Debate History</h3>
                {history.length > 0 && (
                  <div className="fs-history-actions">
                    <button type="button" className="fs-btn fs-btn-small" onClick={() => void importHistoryFromBackend()} disabled={syncing}>
                      {syncing ? 'Working...' : 'Import API'}
                    </button>
                    <button type="button" className="fs-btn fs-btn-small" onClick={() => void syncHistoryToBackend()} disabled={syncing}>
                      {syncing ? 'Working...' : `Sync API${backendBaseUrl ? '' : ' (Set URL)'}`}
                    </button>
                    <button
                      type="button"
                      className="fs-btn fs-btn-small"
                      onClick={() => {
                        const data = JSON.stringify(history, null, 2)
                        downloadTextFile(`flipside-all-debates-${Date.now()}.json`, data)
                      }}
                    >
                      Export JSON ({history.length})
                    </button>
                    <button
                      type="button"
                      className="fs-btn fs-btn-small"
                      onClick={() => downloadTextFile(`flipside-all-debates-${Date.now()}.csv`, csvFromHistory(history))}
                    >
                      Export CSV
                    </button>
                  </div>
                )}
              </div>
              <p className="fs-note">Saved automatically in localStorage. Re-open and export anytime.</p>
              {history.length === 0 && <p className="fs-empty">No saved debates yet. Finish one to see it here.</p>}
              {history.length > 0 && (
                <>
                  <div className="fs-form-grid">
                    <input
                      value={historyQuery}
                      onChange={(event) => setHistoryQuery(event.target.value)}
                      className="fs-input"
                      placeholder="Search by topic, tag, or verdict..."
                      aria-label="Search debate history"
                    />
                    <select
                      value={historyDifficultyFilter}
                      onChange={(event) => setHistoryDifficultyFilter(event.target.value as 'All' | Difficulty)}
                      className="fs-input"
                      aria-label="Filter history by difficulty"
                    >
                      <option value="All">All Difficulty</option>
                      {DIFFICULTIES.map((entry) => (
                        <option key={entry} value={entry}>
                          {entry}
                        </option>
                      ))}
                    </select>
                    <select
                      value={historyWinnerFilter}
                      onChange={(event) => setHistoryWinnerFilter(event.target.value as 'All' | Verdict['winner'])}
                      className="fs-input"
                      aria-label="Filter history by winner"
                    >
                      <option value="All">All Winners</option>
                      <option value="User">User</option>
                      <option value="AI">AI</option>
                    </select>
                    <select
                      value={historyTagFilter}
                      onChange={(event) => setHistoryTagFilter(event.target.value as 'All' | string)}
                      className="fs-input"
                      aria-label="Filter history by tag"
                    >
                      <option value="All">All Tags</option>
                      {allHistoryTags.map((tag) => (
                        <option key={tag} value={tag}>
                          {tag}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="fs-stat-grid">
                    <div className="fs-stat-box">
                      <span>Total Debates</span>
                      <strong>{historyAnalytics.total}</strong>
                    </div>
                    <div className="fs-stat-box">
                      <span>Win Rate</span>
                      <strong>{historyAnalytics.winRate}%</strong>
                    </div>
                    <div className="fs-stat-box">
                      <span>Avg Score (You / AI)</span>
                      <strong>
                        {historyAnalytics.avgUser} / {historyAnalytics.avgAi}
                      </strong>
                    </div>
                    <div className="fs-stat-box">
                      <span>Most Common Tag</span>
                      <strong>{historyAnalytics.topTag}</strong>
                    </div>
                  </div>
                </>
              )}
              <div className="fs-history-list">
                {filteredHistory.slice(0, 8).map((entry) => (
                  <article key={entry.id} className="fs-history-item">
                    <div>
                      <h4>{entry.topic}</h4>
                      <p>
                        {new Date(entry.date).toLocaleString()} | {entry.difficulty} | {entry.side}
                      </p>
                      <p className="fs-scoreline">
                        YOU {entry.userScore} - AI {entry.aiScore} ({entry.verdict.winner})
                      </p>
                      <p className="fs-note">Tags: {entry.tags.join(' • ')}</p>
                    </div>
                    <div className="fs-history-actions">
                      <button type="button" className="fs-btn" onClick={() => previewHistoryEntry(entry)}>
                        View
                      </button>
                      <button
                        type="button"
                        className="fs-btn"
                        onClick={() => {
                          const text = transcriptFromDebate(entry)
                          downloadTextFile(`flipside-history-${entry.id}.txt`, text)
                        }}
                      >
                        Export TXT
                      </button>
                      <button
                        type="button"
                        className="fs-btn"
                        onClick={() => {
                          downloadTextFile(`flipside-history-${entry.id}.md`, markdownFromDebate(entry))
                        }}
                      >
                        Export MD
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              {history.length > 0 && filteredHistory.length === 0 && (
                <p className="fs-empty">No debates match your filters. Try broadening your search.</p>
              )}
            </div>
          </section>
        </div>
      </div>
    )
  }

  if (screen === 'debate') {
    return (
      <div className="fs-page fs-bg-animated">
        <div className="fs-shell fs-shell-narrow">
          <header className="fs-debate-head fs-pop-in">
            <div>
              <p className="fs-eyebrow">{difficulty} Mode</p>
              <h2>{activeTopic}</h2>
              <p className="fs-note">
                Round {round}/{totalRounds} | Engine: {resolvedMode === 'mock' ? 'Mock AI' : 'Gemini'}
              </p>
            </div>
            <div className="fs-head-right">
              <div className={`fs-timer ${timeLeft <= roundTime * 0.2 ? 'is-danger' : ''}`}>
                {Math.floor(Math.max(timeLeft, 0) / 60)}:{String(Math.max(timeLeft, 0) % 60).padStart(2, '0')}
              </div>
              <div className="fs-score">YOU {userScore} - AI {aiScore}</div>
              <div className="fs-score-pct">{scorePct}%</div>
            </div>
          </header>

          <progress
            className={`fs-timer-progress ${timeLeft <= roundTime * 0.2 ? 'is-danger' : ''}`}
            max={roundTime}
            value={Math.max(timeLeft, 0)}
            aria-label="Time remaining in current round"
          />

          {engineNotice && <div className="fs-banner">{engineNotice}</div>}

          <main className="fs-chat">
            {messages.length === 0 && <p className="fs-empty">The floor is yours. Make your opening argument.</p>}
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`fs-msg-row ${message.role === 'user' ? 'is-user' : 'is-ai'}`}
                data-role={message.role}
              >
                <div className={`fs-msg ${message.role === 'user' ? 'is-user' : 'is-ai'} ${message.forfeited ? 'is-forfeit' : ''}`}>
                  {message.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="fs-thinking" aria-live="polite" role="status">
                AI is thinking...
              </div>
            )}
            <div ref={chatEndRef} />
          </main>

          {coachEnabled && coachInsights.length > 0 && (
            <section className="fs-card" aria-live="polite">
              <h3>Coach Panel</h3>
              <p className="fs-note">
                Clarity {coachAverages.clarity} | Evidence {coachAverages.evidence} | Structure {coachAverages.structure} |
                Rebuttal {coachAverages.rebuttal}
              </p>
              <p>{coachInsights[coachInsights.length - 1]?.tip}</p>
            </section>
          )}

          <footer className="fs-input-row">
            <input
              ref={inputRef}
              className="fs-input"
              placeholder={loading ? 'Please wait for response...' : 'Type your argument and press Enter'}
              disabled={loading}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void sendMessage()
                }
              }}
            />
              <button type="button" className="fs-btn fs-btn-primary" onClick={() => void sendMessage()} disabled={loading}>
                Send
              </button>
            <button type="button" className="fs-btn" onClick={() => void handleForfeit()} disabled={loading}>
              Forfeit
            </button>
          </footer>
        </div>
      </div>
    )
  }

  return (
    <div className="fs-page fs-bg-animated">
      <div className="fs-shell fs-shell-narrow">
        <section className="fs-card fs-pop-in">
          <p className="fs-eyebrow">Final Verdict</p>
          <h2 className={verdict?.winner === 'User' ? 'fs-win' : 'fs-lose'}>
            {verdict?.winner === 'User' ? 'You Won' : 'AI Won'}
          </h2>
          <p>{verdict?.summary}</p>

          <div className="fs-stat-grid">
            <div className="fs-stat-box">
              <span>Your Score</span>
              <strong>{userScore}</strong>
            </div>
            <div className="fs-stat-box">
              <span>AI Score</span>
              <strong>{aiScore}</strong>
            </div>
            <div className="fs-stat-box">
              <span>Average</span>
              <strong>
                {avgUser} / {avgAi}
              </strong>
            </div>
          </div>

          <div className="fs-breakdown">
            {roundScores.map((score, index) => (
              <div key={`score-${index}`} className="fs-break-item">
                <span>
                  R{index + 1}: {score.reason}
                </span>
                <strong>
                  {score.userPoints}-{score.aiPoints}
                </strong>
              </div>
            ))}
          </div>

          <div className="fs-two-col">
            <div>
              <h4>Strengths</h4>
              <ul>
                {verdict?.strengths.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Weaknesses</h4>
              <ul>
                {verdict?.weaknesses.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          {coachEnabled && coachInsights.length > 0 && (
            <div className="fs-breakdown">
              <h4>Coach Review</h4>
              {coachInsights.map((insight) => (
                <div key={`coach-${insight.round}`} className="fs-break-item">
                  <span>
                    R{insight.round}: Clarity {insight.clarity} | Evidence {insight.evidence} | Structure {insight.structure} |
                    Rebuttal {insight.rebuttal}
                  </span>
                  <strong>{insight.tip}</strong>
                </div>
              ))}
            </div>
          )}

          <p className="fs-mvp">
            MVP argument: <em>{verdict?.mvpArgument}</em>
          </p>

          <div className="fs-action-row">
            <button type="button" className="fs-btn" onClick={() => void exportCurrentTranscript()}>
              {copied ? 'Copied' : 'Copy Transcript'}
            </button>
            <button type="button" className="fs-btn" onClick={downloadCurrentTranscript}>
              Download Transcript
            </button>
            <button
              type="button"
              className="fs-btn"
              onClick={() => {
                setMessages([])
                setRoundScores([])
                setRound(0)
                setUserScore(0)
                setAiScore(0)
                setVerdict(null)
                setScreen('debate')
                startTimer()
              }}
            >
              Rematch
            </button>
            <button type="button" className="fs-btn fs-btn-primary" onClick={reset}>
              New Debate
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
