import type { Message, DebateMode, Verdict } from './types'
import { getSystemPrompt, getCoachPrompt, getVerdictPrompt } from './aiPrompts'

type RequestMethod = 'GET' | 'POST'

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.trim().replace(/\/+$/, '')

const requestJson = async <T>(baseUrl: string, path: string, method: RequestMethod, body?: unknown): Promise<T> => {
  const url = `${normalizeBaseUrl(baseUrl)}${path}`
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })

  const payload = (await response.json()) as { ok?: boolean; error?: unknown }
  if (!response.ok || payload.ok === false) {
    const message = typeof payload.error === 'string' ? payload.error : `Request failed: ${method} ${path}`
    throw new Error(message)
  }

  return payload as T
}

// Backend health check
export const checkBackendHealth = async (baseUrl: string): Promise<void> => {
  await requestJson<{ ok?: boolean }>(baseUrl, '/health', 'GET')
}

// History sync
export const pushHistoryToBackend = async <T>(baseUrl: string, items: T[]): Promise<number> => {
  const payload = await requestJson<{ saved?: number }>(baseUrl, '/v1/history', 'POST', { items })
  return typeof payload.saved === 'number' ? payload.saved : items.length
}

export const pullHistoryFromBackend = async <T>(baseUrl: string): Promise<T[]> => {
  const payload = await requestJson<{ items?: unknown }>(baseUrl, '/v1/history', 'GET')
  return Array.isArray(payload.items) ? (payload.items as T[]) : []
}

// Multiplayer room
export const createBackendRoom = async (baseUrl: string, topic: string, createdBy: string): Promise<string> => {
  const payload = await requestJson<{ room?: { roomCode?: unknown } }>(baseUrl, '/v1/multiplayer/rooms', 'POST', {
    topic,
    createdBy,
  })

  const code = payload.room && typeof payload.room.roomCode === 'string' ? payload.room.roomCode : ''
  if (!code) throw new Error('Backend did not return a room code.')
  return code
}

// Anthropic Claude API client
interface AnthropicMessage {
  role: 'user' | 'assistant'
  content: string
}

interface AnthropicResponse {
  content: Array<{ type: string; text: string }>
}

export async function callAnthropicAPI(
  apiKey: string,
  messages: Message[],
  mode: DebateMode,
  topic: string,
  userSide: 'for' | 'against',
  roundNumber: number,
  totalRounds: number
): Promise<string> {
  const systemPrompt = getSystemPrompt(topic, mode, userSide, roundNumber, totalRounds)
  
  const anthropicMessages: AnthropicMessage[] = messages.map((m) => ({
    role: m.role === 'user' ? 'user' : 'assistant',
    content: m.content,
  }))

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1024,
      system: systemPrompt,
      messages: anthropicMessages,
    }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(
      (errorData as { error?: { message?: string } })?.error?.message || 
      `Anthropic API error: ${response.status}`
    )
  }

  const data = await response.json() as AnthropicResponse
  return data.content[0]?.text || ''
}

export async function getCoachTip(
  apiKey: string,
  topic: string,
  userSide: 'for' | 'against',
  lastUserMessage: string,
  lastAiMessage: string
): Promise<string> {
  const prompt = getCoachPrompt(topic, userSide, lastUserMessage, lastAiMessage)

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 256,
      messages: [{ role: 'user', content: prompt }],
    }),
  })

  if (!response.ok) {
    throw new Error('Failed to get coach tip')
  }

  const data = await response.json() as AnthropicResponse
  return data.content[0]?.text || ''
}

export async function getDebateVerdict(
  apiKey: string,
  topic: string,
  userSide: 'for' | 'against',
  userScore: number,
  aiScore: number,
  messages: Message[]
): Promise<Verdict> {
  // Create a summary of key exchanges
  const messagesSummary = messages
    .slice(-10)
    .map((m) => `${m.role === 'user' ? 'User' : 'FlipSide'}: ${m.content.slice(0, 100)}...`)
    .join('\n')

  const prompt = getVerdictPrompt(topic, userSide, userScore, aiScore, messagesSummary)

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1024,
      messages: [{ role: 'user', content: prompt }],
    }),
  })

  if (!response.ok) {
    throw new Error('Failed to get verdict')
  }

  const data = await response.json() as AnthropicResponse
  const text = data.content[0]?.text || '{}'
  
  try {
    // Extract JSON from response (it might be wrapped in markdown code blocks)
    const jsonMatch = text.match(/\{[\s\S]*\}/)
    if (!jsonMatch) throw new Error('No JSON found')
    return JSON.parse(jsonMatch[0]) as Verdict
  } catch {
    // Return a default verdict if parsing fails
    return {
      winner: userScore > aiScore ? 'user' : aiScore > userScore ? 'ai' : 'tie',
      summary: 'The debate has concluded.',
      strengths: ['Good effort'],
      weaknesses: ['Room for improvement'],
      overallAnalysis: 'Thank you for participating in this debate.',
    }
  }
}

// Mock AI for when no API key is available
export function getMockAIResponse(
  _messages: Message[],
  mode: DebateMode,
  topic: string,
  userSide: 'for' | 'against'
): string {
  const aiSide = userSide === 'for' ? 'against' : 'for'
  const sideLabel = aiSide === 'for' ? 'in favor of' : 'against'
  
  const responses = {
    casual: [
      `That's an interesting point, but consider this perspective ${sideLabel} "${topic}": there are multiple factors we should weigh carefully before reaching a conclusion.`,
      `I appreciate your argument, though I'd like to offer a different view ${sideLabel} this topic. What about the long-term implications?`,
    ],
    balanced: [
      `While I understand your reasoning, the evidence ${sideLabel} "${topic}" suggests otherwise. Studies have shown that the implications are more nuanced than they appear.`,
      `Your point has merit, but let me present a counterargument ${sideLabel} this position. We must consider both the immediate and systemic effects.`,
    ],
    intense: [
      `Your argument contains a fundamental flaw. The premise that supports your position ${sideLabel === 'in favor of' ? 'against' : 'for'} "${topic}" fails to account for critical variables. Allow me to deconstruct this systematically.`,
      `While rhetorically appealing, your argument lacks empirical foundation. The evidence ${sideLabel} this topic is overwhelming when examined rigorously.`,
    ],
  }
  
  const modeResponses = responses[mode]
  return modeResponses[Math.floor(Math.random() * modeResponses.length)]
}

