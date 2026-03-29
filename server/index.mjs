import { createServer } from 'node:http'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const dataDir = join(__dirname, 'data')
const historyFile = join(dataDir, 'history.json')
const roomsFile = join(dataDir, 'rooms.json')
const webhookEventsFile = join(dataDir, 'webhook-events.json')

const PORT = Number(process.env.PORT || 8787)
const CORS_ORIGIN = process.env.CORS_ORIGIN || '*'
const MAX_BODY_BYTES = 1024 * 1024
const HISTORY_LIMIT = 2000

const baseHeaders = {
  'Access-Control-Allow-Origin': CORS_ORIGIN,
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key',
  'Content-Type': 'application/json; charset=utf-8',
}

const ensureDataDir = async () => {
  await mkdir(dataDir, { recursive: true })
}

const readJsonArray = async (path) => {
  try {
    const raw = await readFile(path, 'utf8')
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch (error) {
    if (error && typeof error === 'object' && 'code' in error && error.code === 'ENOENT') return []
    throw error
  }
}

const writeJsonArray = async (path, data) => {
  await ensureDataDir()
  await writeFile(path, `${JSON.stringify(data, null, 2)}\n`, 'utf8')
}

const nowIso = () => new Date().toISOString()

const send = (res, statusCode, payload) => {
  res.writeHead(statusCode, baseHeaders)
  res.end(JSON.stringify(payload))
}

const readBody = async (req) =>
  new Promise((resolve, reject) => {
    let size = 0
    const chunks = []

    req.on('data', (chunk) => {
      size += chunk.length
      if (size > MAX_BODY_BYTES) {
        reject(new Error('Payload too large'))
        req.destroy()
        return
      }
      chunks.push(chunk)
    })

    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8')
      if (!raw.trim()) {
        resolve({})
        return
      }

      try {
        resolve(JSON.parse(raw))
      } catch {
        reject(new Error('Invalid JSON body'))
      }
    })

    req.on('error', reject)
  })

const normalizeHistoryEntry = (entry) => {
  if (!entry || typeof entry !== 'object') throw new Error('Invalid history payload')
  if (typeof entry.topic !== 'string' || !entry.topic.trim()) throw new Error('History topic is required')

  return {
    ...entry,
    id: typeof entry.id === 'string' && entry.id ? entry.id : randomUUID(),
    date: typeof entry.date === 'string' && entry.date ? entry.date : nowIso(),
    tags: Array.isArray(entry.tags) ? entry.tags : [],
    messages: Array.isArray(entry.messages) ? entry.messages : [],
    roundScores: Array.isArray(entry.roundScores) ? entry.roundScores : [],
  }
}

const createRoom = (payload) => {
  const roomCode =
    typeof payload.roomCode === 'string' && payload.roomCode.trim()
      ? payload.roomCode.trim().toUpperCase()
      : Math.random().toString(36).slice(2, 8).toUpperCase()

  const topic = typeof payload.topic === 'string' ? payload.topic.trim() : ''
  const createdBy = typeof payload.createdBy === 'string' && payload.createdBy.trim() ? payload.createdBy.trim() : 'anonymous'

  return {
    id: randomUUID(),
    roomCode,
    topic,
    createdBy,
    createdAt: nowIso(),
    status: 'open',
  }
}

const authorizeWebhook = (req) => {
  const expected = process.env.WEBHOOK_SECRET
  if (!expected) return true
  const given = req.headers['x-api-key']
  return given === expected
}

const difficultyGuide = {
  casual: 'friendly, concise, low aggression, explain simply',
  balanced: 'assertive but fair, challenge assumptions with evidence framing',
  intense: 'high rigor, precise rebuttals, pressure-test logic and weak premises',
}

const deterministicHash = (value) => {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0
  }
  return hash
}

const NEWS_FALLBACK_TOPICS = [
  { title: 'AI regulation and public accountability', source: 'fallback-curated', summary: 'How governments can audit and govern high-impact AI systems.', url: 'https://example.local/fallback/ai-regulation' },
  { title: 'Climate adaptation funding priorities', source: 'fallback-curated', summary: 'Debate if climate funding should prioritize adaptation over mitigation.', url: 'https://example.local/fallback/climate-funding' },
  { title: 'Data privacy versus platform personalization', source: 'fallback-curated', summary: 'Should user privacy limits reduce recommendation performance?', url: 'https://example.local/fallback/privacy-personalization' },
  { title: 'Universal basic income and labor incentives', source: 'fallback-curated', summary: 'Can UBI improve resilience without reducing workforce participation?', url: 'https://example.local/fallback/ubi-labor' },
  { title: 'Nuclear energy in net-zero strategies', source: 'fallback-curated', summary: 'Should nuclear be central in long-term clean energy plans?', url: 'https://example.local/fallback/nuclear-netzero' },
  { title: 'Social media age restrictions effectiveness', source: 'fallback-curated', summary: 'Do age-gating rules improve safety or just shift risk elsewhere?', url: 'https://example.local/fallback/social-age-gate' },
  { title: 'Remote work productivity and culture trade-offs', source: 'fallback-curated', summary: 'Is hybrid work the best default for innovation-heavy teams?', url: 'https://example.local/fallback/remote-hybrid' },
  { title: 'Open-source AI safety obligations', source: 'fallback-curated', summary: 'Should open-weight model publishers hold post-release safety duties?', url: 'https://example.local/fallback/oss-ai-safety' },
]

const buildDeterministicFallbackNews = (query, limit) => {
  const normalized = query.trim().toLowerCase() || 'technology'
  const start = deterministicHash(normalized) % NEWS_FALLBACK_TOPICS.length
  const topics = []
  for (let i = 0; i < limit; i += 1) {
    topics.push(NEWS_FALLBACK_TOPICS[(start + i) % NEWS_FALLBACK_TOPICS.length])
  }
  return topics
}

const fetchNewsApi = async (query, limit, apiKey) => {
  const safeQuery = encodeURIComponent(query)
  const url = `https://newsapi.org/v2/everything?q=${safeQuery}&pageSize=${limit}&sortBy=publishedAt&language=en`
  const response = await fetch(url, {
    headers: {
      'X-Api-Key': apiKey,
    },
  })

  if (!response.ok) {
    const details = await response.text().catch(() => '')
    throw new Error(`NewsAPI request failed (${response.status}): ${details.slice(0, 180)}`)
  }

  const payload = await response.json()
  if (!payload || !Array.isArray(payload.articles)) {
    throw new Error('NewsAPI returned invalid payload.')
  }

  return payload.articles
    .filter((article) => article && typeof article.title === 'string' && article.title.trim())
    .slice(0, limit)
    .map((article) => ({
      title: article.title.trim(),
      source: typeof article?.source?.name === 'string' ? article.source.name : 'newsapi',
      summary: typeof article.description === 'string' ? article.description : '',
      url: typeof article.url === 'string' ? article.url : '',
    }))
}

const extractLatestUserArgument = (messages) => {
  const reversed = [...messages].reverse()
  const found = reversed.find((m) => m && m.role === 'user' && typeof m.content === 'string')
  return found ? found.content.trim() : ''
}

const generateFallbackDebateReply = ({ topic, mode, userSide, roundNumber, totalRounds, messages }) => {
  const aiSide = userSide === 'for' ? 'against' : 'for'
  const latest = extractLatestUserArgument(messages)
  const openers = [
    `Round ${roundNumber}/${totalRounds}: I’m arguing ${aiSide} this motion.`,
    `I’ll challenge that from the ${aiSide} side.`,
    `I disagree from the ${aiSide} position for concrete reasons.`,
  ]
  const opener = openers[Math.floor(Math.random() * openers.length)]

  const modeBlocks = {
    casual: `Your point is thoughtful, but it overlooks trade-offs. If we prioritize only one benefit, we risk side effects that make the outcome worse over time.`,
    balanced: `Your claim assumes best-case outcomes and underweights implementation risk. Policy and market behavior usually introduce second-order effects that weaken that conclusion.`,
    intense: `Your argument depends on an unproven premise and a weak causal leap. Without robust evidence and counterfactual control, the conclusion is not defensible at decision-grade quality.`,
  }

  const evidenceAngles = [
    `On "${topic}", the strongest counterpoint is incentive design: people respond to rules, not intentions.`,
    `On "${topic}", feasibility matters: scaling often breaks assumptions that look valid in theory.`,
    `On "${topic}", distribution effects are critical: who benefits first is usually not who bears the cost.`,
  ]
  const angle = evidenceAngles[Math.floor(Math.random() * evidenceAngles.length)]

  const userRef = latest
    ? `You said: "${latest.slice(0, 140)}${latest.length > 140 ? '…' : ''}". That still doesn’t solve the structural downside.`
    : `Your previous argument still leaves a structural downside unaddressed.`

  const closer = mode === 'intense'
    ? 'Prove the premise with concrete evidence and show why the alternative interpretation is weaker.'
    : 'Address that directly with one specific example and one measurable outcome.'

  return `${opener}\n\n${modeBlocks[mode]}\n\n${angle}\n${userRef}\n\n${closer}`
}

const callAnthropicDebate = async (apiKey, payload) => {
  const { topic, mode, userSide, roundNumber, totalRounds, messages } = payload
  const aiSide = userSide === 'for' ? 'against' : 'for'
  const system = `You are FlipSide, an AI debate opponent.\nDebate topic: "${topic}"\nYou must argue: ${aiSide}\nDifficulty: ${mode} (${difficultyGuide[mode] || difficultyGuide.balanced})\nCurrent round: ${roundNumber}/${totalRounds}\nRules: respond with a direct debate rebuttal only, no markdown, no bullet list unless needed for clarity, max 170 words.`
  const anthropicMessages = messages
    .filter((m) => m && typeof m.content === 'string' && (m.role === 'user' || m.role === 'ai'))
    .map((m) => ({
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
      max_tokens: 400,
      system,
      messages: anthropicMessages,
    }),
  })

  if (!response.ok) {
    const fallbackText = await response.text().catch(() => '')
    throw new Error(`Anthropic request failed (${response.status}): ${fallbackText.slice(0, 180)}`)
  }

  const data = await response.json()
  const text = Array.isArray(data?.content) ? data.content[0]?.text : ''
  if (!text || typeof text !== 'string') {
    throw new Error('Anthropic returned an empty response.')
  }
  return text.trim()
}

const server = createServer(async (req, res) => {
  try {
    const method = req.method || 'GET'
    const requestUrl = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`)
    const path = requestUrl.pathname

    if (method === 'OPTIONS') {
      res.writeHead(204, baseHeaders)
      res.end()
      return
    }

    if (method === 'GET' && path === '/health') {
      send(res, 200, {
        ok: true,
        service: 'flipside2-api',
        version: 1,
        time: nowIso(),
      })
      return
    }

    if (method === 'GET' && path === '/v1/history') {
      const items = await readJsonArray(historyFile)
      send(res, 200, {
        ok: true,
        count: items.length,
        items,
      })
      return
    }

    if (method === 'POST' && path === '/v1/history') {
      const body = await readBody(req)
      const incoming = Array.isArray(body.items) ? body.items : Array.isArray(body.history) ? body.history : [body]
      const normalized = incoming.map(normalizeHistoryEntry)

      const existing = await readJsonArray(historyFile)
      const merged = [...normalized, ...existing].slice(0, HISTORY_LIMIT)

      await writeJsonArray(historyFile, merged)
      send(res, 201, {
        ok: true,
        saved: normalized.length,
        count: merged.length,
      })
      return
    }

    if (method === 'POST' && path === '/v1/multiplayer/rooms') {
      const body = await readBody(req)
      const room = createRoom(body)
      const rooms = await readJsonArray(roomsFile)
      const updated = [room, ...rooms].slice(0, HISTORY_LIMIT)
      await writeJsonArray(roomsFile, updated)

      send(res, 201, {
        ok: true,
        room,
      })
      return
    }

    if (method === 'POST' && path === '/v1/webhooks/events') {
      if (!authorizeWebhook(req)) {
        send(res, 401, { ok: false, error: 'Unauthorized webhook call.' })
        return
      }

      const body = await readBody(req)
      const event = {
        id: randomUUID(),
        type: typeof body.type === 'string' ? body.type : 'unknown',
        payload: body.payload ?? body,
        receivedAt: nowIso(),
      }

      const events = await readJsonArray(webhookEventsFile)
      const updated = [event, ...events].slice(0, HISTORY_LIMIT)
      await writeJsonArray(webhookEventsFile, updated)

      send(res, 202, {
        ok: true,
        eventId: event.id,
      })
      return
    }

    if (method === 'POST' && path === '/v1/debate') {
      const body = await readBody(req)
      const payload = {
        topic: typeof body.topic === 'string' ? body.topic.trim() : '',
        mode: typeof body.mode === 'string' ? body.mode : 'balanced',
        userSide: body.userSide === 'against' ? 'against' : 'for',
        roundNumber: Number.isFinite(Number(body.roundNumber)) ? Number(body.roundNumber) : 1,
        totalRounds: Number.isFinite(Number(body.totalRounds)) ? Number(body.totalRounds) : 5,
        messages: Array.isArray(body.messages) ? body.messages : [],
      }

      if (!payload.topic) {
        send(res, 400, { ok: false, error: 'Topic is required.' })
        return
      }

      const apiKeyFromHeader = typeof req.headers['x-api-key'] === 'string' ? req.headers['x-api-key'] : ''
      const serverApiKey = process.env.ANTHROPIC_API_KEY || ''
      const apiKey = apiKeyFromHeader || serverApiKey

      if (apiKey) {
        try {
          const reply = await callAnthropicDebate(apiKey, payload)
          send(res, 200, { ok: true, reply, source: 'anthropic' })
          return
        } catch (error) {
          const cause = error instanceof Error ? error.message : 'Anthropic request failed'
          const reply = generateFallbackDebateReply(payload)
          send(res, 200, { ok: true, reply, source: 'fallback', warning: cause })
          return
        }
      }

      const reply = generateFallbackDebateReply(payload)
      send(res, 200, { ok: true, reply, source: 'fallback' })
      return
    }

    if (method === 'GET' && path === '/v1/news') {
      const q = (requestUrl.searchParams.get('q') || '').trim()
      const query = q || 'technology policy'
      const requestedLimit = Number(requestUrl.searchParams.get('limit') || 6)
      const limit = Math.min(10, Math.max(3, Number.isFinite(requestedLimit) ? Math.round(requestedLimit) : 6))
      const newsApiKey = process.env.NEWS_API_KEY || ''

      if (!newsApiKey) {
        const suggestions = buildDeterministicFallbackNews(query, limit)
        send(res, 200, {
          ok: true,
          source: 'fallback',
          suggestions,
        })
        return
      }

      try {
        const suggestions = await fetchNewsApi(query, limit, newsApiKey)
        send(res, 200, {
          ok: true,
          source: 'newsapi',
          suggestions: suggestions.length > 0 ? suggestions : buildDeterministicFallbackNews(query, limit),
        })
      } catch (error) {
        const cause = error instanceof Error ? error.message : 'Unknown NewsAPI failure'
        send(res, 200, {
          ok: true,
          source: 'fallback',
          warning: cause,
          suggestions: buildDeterministicFallbackNews(query, limit),
        })
      }
      return
    }

    send(res, 404, {
      ok: false,
      error: `Route not found: ${method} ${path}`,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown server error'
    send(res, 500, { ok: false, error: message })
  }
})

await ensureDataDir()
server.listen(PORT, () => {
  console.log(`FlipSide backend listening on http://localhost:${PORT}`)
})
