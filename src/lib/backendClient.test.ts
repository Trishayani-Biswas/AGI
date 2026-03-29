import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  checkBackendHealth,
  runAriaResearch,
} from './backendClient'

const mockJsonResponse = (payload: unknown, status = 200): Response =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('backendClient', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('checks backend health via /health', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockJsonResponse({ ok: true }))

    await expect(checkBackendHealth('http://localhost:8787')).resolves.toBeUndefined()

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8787/health', expect.objectContaining({ method: 'GET' }))
  })

  it('runs ARIA research and returns the run payload', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        mockJsonResponse({
          ok: true,
          run: {
            id: 'run-1',
            createdAt: '2025-01-01T00:00:00.000Z',
            topic: 'Should cities ban private cars?',
            depth: 'standard',
            agents: {
              advocate: { summary: 'Advocate summary' },
              skeptic: { summary: 'Skeptic summary' },
              domain: { summary: 'Domain summary' },
              arbitrator: { summary: 'Arbitrator summary' },
            },
            claims: [],
            contradictions: [],
            knowledgeGaps: [],
            evidence: [],
            metadata: {
              sourceMode: 'deterministic',
              generatedAt: '2025-01-01T00:00:00.000Z',
              maxSources: 6,
            },
          },
        })
      )

    const run = await runAriaResearch(
      'http://localhost:8787',
      {
        topic: 'Should cities ban private cars?',
        depth: 'standard',
        maxSources: 6,
      }
    )

    expect(run.id).toBe('run-1')
    expect(run.topic).toBe('Should cities ban private cars?')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8787/v1/research/run',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
        }),
      })
    )
  })

  it('throws when research route responds without run payload', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockJsonResponse({
        ok: true,
      })
    )

    await expect(
      runAriaResearch('http://localhost:8787', { topic: 'Policy reform' })
    ).rejects.toThrow('Backend did not return a research run.')
  })

  it('throws when API reports failure payload', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockJsonResponse({ ok: false, error: 'Backend failure' }, 200)
    )

    await expect(checkBackendHealth('http://localhost:8787')).rejects.toThrow('Backend failure')
  })
})
