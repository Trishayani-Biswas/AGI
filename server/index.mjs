import { createServer } from 'node:http'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'
import { normalizeResearchRequest, runAriaResearch } from './aria/orchestrator.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const dataDir = join(__dirname, 'data')
const researchRunsFile = join(dataDir, 'research-runs.json')

const PORT = Number(process.env.PORT || 8787)
const CORS_ORIGIN = process.env.CORS_ORIGIN || '*'
const MAX_BODY_BYTES = 1024 * 1024
const RESEARCH_RUNS_LIMIT = 500

const baseHeaders = {
  'Access-Control-Allow-Origin': CORS_ORIGIN,
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type,X-Api-Key',
  'Content-Type': 'application/json; charset=utf-8',
}

const nowIso = () => new Date().toISOString()

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
        mode: 'aria-research',
        time: nowIso(),
      })
      return
    }

    if (method === 'POST' && path === '/v1/research/run') {
      const body = await readBody(req)
      const payload = normalizeResearchRequest(body)

      if (!payload.topic) {
        send(res, 400, { ok: false, error: 'Topic is required.' })
        return
      }

      const output = await runAriaResearch(payload)
      const run = {
        id: randomUUID(),
        createdAt: nowIso(),
        ...output,
      }

      const existing = await readJsonArray(researchRunsFile)
      const merged = [run, ...existing].slice(0, RESEARCH_RUNS_LIMIT)
      await writeJsonArray(researchRunsFile, merged)

      send(res, 200, {
        ok: true,
        run,
      })
      return
    }

    if (method === 'GET' && path === '/v1/research') {
      const requestedLimit = Number(requestUrl.searchParams.get('limit') || 10)
      const limit = Math.min(50, Math.max(1, Number.isFinite(requestedLimit) ? Math.round(requestedLimit) : 10))
      const runs = await readJsonArray(researchRunsFile)

      send(res, 200, {
        ok: true,
        count: runs.length,
        items: runs.slice(0, limit).map((run) => ({
          id: run.id,
          topic: run.topic,
          createdAt: run.createdAt,
          summary: run?.agents?.arbitrator?.summary || '',
        })),
      })
      return
    }

    if (method === 'GET' && path.startsWith('/v1/research/')) {
      const runId = decodeURIComponent(path.slice('/v1/research/'.length)).trim()
      if (!runId) {
        send(res, 400, { ok: false, error: 'Research run id is required.' })
        return
      }

      const runs = await readJsonArray(researchRunsFile)
      const run = runs.find((item) => item && item.id === runId)
      if (!run) {
        send(res, 404, { ok: false, error: 'Research run not found.' })
        return
      }

      send(res, 200, {
        ok: true,
        run,
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
