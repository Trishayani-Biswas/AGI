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
