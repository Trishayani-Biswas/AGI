import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  callDebateBackend,
  checkBackendHealth,
  getNewsTopicSuggestions,
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

  it('sends debate request with API key header and returns reply', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(mockJsonResponse({ ok: true, reply: 'Test reply', source: 'openai' }))

    const reply = await callDebateBackend(
      'http://localhost:8787',
      {
        topic: 'Should cities ban private cars?',
        mode: 'balanced',
        userSide: 'for',
        roundNumber: 1,
        totalRounds: 5,
        messages: [],
      },
      'test-key'
    )

    expect(reply).toBe('Test reply')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8787/v1/debate',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-Api-Key': 'test-key',
        }),
      })
    )
  })

  it('maps and filters news topic suggestions from API response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockJsonResponse({
        ok: true,
        source: 'newsapi',
        suggestions: [
          { title: 'AI safety hearings', source: 'Reuters', summary: 'Policy debate', url: 'https://example.com/1' },
          { title: '', source: 'Invalid', summary: 'Should be filtered', url: 'https://example.com/2' },
          { title: 'Public transit expansion', source: null, summary: null, url: null },
        ],
      })
    )

    const topics = await getNewsTopicSuggestions('http://localhost:8787', 'policy', 4)

    expect(topics).toEqual([
      {
        title: 'AI safety hearings',
        source: 'Reuters',
        summary: 'Policy debate',
        url: 'https://example.com/1',
      },
      {
        title: 'Public transit expansion',
        source: 'newsapi',
        summary: '',
        url: '',
      },
    ])
  })

  it('throws when API reports failure payload', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      mockJsonResponse({ ok: false, error: 'Backend failure' }, 200)
    )

    await expect(checkBackendHealth('http://localhost:8787')).rejects.toThrow('Backend failure')
  })
})
