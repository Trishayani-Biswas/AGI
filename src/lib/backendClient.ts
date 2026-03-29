type RequestMethod = 'GET' | 'POST'

const normalizeBaseUrl = (baseUrl: string): string => baseUrl.trim().replace(/\/+$/, '')

interface ApiErrorPayload {
  ok?: boolean
  error?: unknown
  message?: unknown
}

const requestJson = async <T>(
  baseUrl: string,
  path: string,
  method: RequestMethod,
  body?: unknown,
  extraHeaders?: Record<string, string>
): Promise<T> => {
  const url = `${normalizeBaseUrl(baseUrl)}${path}`
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
    body: body ? JSON.stringify(body) : undefined,
  })

  const rawText = await response.text()
  let payload: ApiErrorPayload = {}
  if (rawText.trim()) {
    try {
      payload = JSON.parse(rawText) as ApiErrorPayload
    } catch {
      payload = { error: rawText }
    }
  }

  if (!response.ok || payload.ok === false) {
    const payloadMessage =
      typeof payload.error === 'string'
        ? payload.error
        : typeof payload.message === 'string'
          ? payload.message
          : ''
    const message = payloadMessage || `Request failed: ${method} ${path} (${response.status})`
    throw new Error(message)
  }

  return payload as T
}

// Backend health check
export const checkBackendHealth = async (baseUrl: string): Promise<void> => {
  await requestJson<{ ok?: boolean }>(baseUrl, '/health', 'GET')
}

export interface AriaClaim {
  id: string
  side: 'support' | 'challenge' | 'baseline'
  text: string
  evidenceIds: string[]
  confidence: number
  contradictions: string[]
}

export interface AriaEvidence {
  id: string
  source: string
  url: string
  title: string
  excerpt: string
  relevance: number
  tags: string[]
}

export interface AriaResearchRun {
  id: string
  createdAt: string
  topic: string
  depth: 'quick' | 'standard' | 'deep'
  agents: {
    advocate: { summary: string }
    skeptic: { summary: string }
    domain: { summary: string }
    arbitrator: { summary: string }
  }
  claims: AriaClaim[]
  contradictions: Array<{ id: string; statement: string; involvedClaimIds: string[] }>
  knowledgeGaps: string[]
  evidence: AriaEvidence[]
  metadata: {
    sourceMode: string
    generatedAt: string
    maxSources: number
  }
}

interface ResearchRunResponse {
  ok: boolean
  run?: AriaResearchRun
}

export async function runAriaResearch(
  baseUrl: string,
  payload: {
    topic: string
    depth?: 'quick' | 'standard' | 'deep'
    maxSources?: number
  }
): Promise<AriaResearchRun> {
  const response = await requestJson<ResearchRunResponse>(
    baseUrl,
    '/v1/research/run',
    'POST',
    payload,
  )

  if (!response.run) {
    throw new Error('Backend did not return a research run.')
  }

  return response.run
}

