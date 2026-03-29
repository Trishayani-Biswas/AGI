import { describe, expect, it } from 'vitest'
import {
  calculateFinalVerdict,
  calculateRoundScore,
  determineRoundWinner,
  getAverageResponseTime,
  getStrongestRound,
  getWeakestRound,
} from './scoring'
import type { Message, Round } from './types'

describe('scoring helpers', () => {
  it('determineRoundWinner returns correct winner or tie', () => {
    expect(determineRoundWinner(3, 1)).toBe('user')
    expect(determineRoundWinner(1, 3)).toBe('ai')
    expect(determineRoundWinner(2, 2)).toBe('tie')
  })

  it('calculateRoundScore returns values in 1..3 range', () => {
    const userMessage: Message = {
      id: 'u1',
      role: 'user',
      content: 'Because evidence and data suggest this works in practice.',
      timestamp: Date.now(),
      roundNumber: 1,
    }

    const aiMessage: Message = {
      id: 'a1',
      role: 'ai',
      content: 'However, implementation risk can reduce those gains.',
      timestamp: Date.now(),
      roundNumber: 1,
    }

    const result = calculateRoundScore(userMessage, aiMessage, 'balanced', 45, 120)

    expect(result.userScore).toBeGreaterThanOrEqual(1)
    expect(result.userScore).toBeLessThanOrEqual(3)
    expect(result.aiScore).toBeGreaterThanOrEqual(1)
    expect(result.aiScore).toBeLessThanOrEqual(3)
  })

  it('aggregate helpers compute expected values', () => {
    const rounds: Round[] = [
      { number: 1, winner: 'user', userScore: 3, aiScore: 1, duration: 80 },
      { number: 2, winner: 'ai', userScore: 1, aiScore: 3, duration: 100 },
      { number: 3, winner: 'user', userScore: 2, aiScore: 1, duration: 60 },
    ]

    const verdict = calculateFinalVerdict(rounds)
    expect(verdict.totalUser).toBe(6)
    expect(verdict.totalAi).toBe(5)
    expect(verdict.winner).toBe('user')

    expect(getAverageResponseTime(rounds)).toBe(80)
    expect(getStrongestRound(rounds)).toBe(1)
    expect(getWeakestRound(rounds)).toBe(2)
  })
})
