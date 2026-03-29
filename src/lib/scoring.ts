import type { Message, Round, DebateMode } from './types'

interface ScoringFactors {
  argumentLength: number
  keywordDensity: number
  responseTime: number
  structureScore: number
}

// Keywords that indicate strong argumentation
const STRONG_ARGUMENT_KEYWORDS = [
  'because', 'therefore', 'however', 'furthermore', 'moreover',
  'evidence', 'research', 'studies', 'data', 'statistics',
  'example', 'specifically', 'in fact', 'consider',
  'firstly', 'secondly', 'finally', 'in conclusion',
]

const WEAK_ARGUMENT_KEYWORDS = [
  'maybe', 'probably', 'i think', 'i guess', 'i feel',
  'kind of', 'sort of', 'like',
]

function analyzeArgument(content: string): ScoringFactors {
  const words = content.toLowerCase().split(/\s+/)
  const wordCount = words.length
  
  // Argument length score (optimal: 50-150 words)
  let argumentLength: number
  if (wordCount < 20) {
    argumentLength = 0.3
  } else if (wordCount < 50) {
    argumentLength = 0.6
  } else if (wordCount <= 150) {
    argumentLength = 1.0
  } else if (wordCount <= 250) {
    argumentLength = 0.8
  } else {
    argumentLength = 0.6
  }
  
  // Keyword density (strong vs weak language)
  const strongCount = STRONG_ARGUMENT_KEYWORDS.filter(
    (kw) => content.toLowerCase().includes(kw)
  ).length
  const weakCount = WEAK_ARGUMENT_KEYWORDS.filter(
    (kw) => content.toLowerCase().includes(kw)
  ).length
  
  const keywordDensity = Math.min(1, (strongCount * 0.15) - (weakCount * 0.1) + 0.5)
  
  // Structure score (paragraphs, clear points)
  const hasParagraphs = content.includes('\n\n')
  const hasNumberedPoints = /\d\.|\d\)/.test(content)
  const hasClearStructure = hasParagraphs || hasNumberedPoints
  const structureScore = hasClearStructure ? 1.0 : 0.7
  
  return {
    argumentLength,
    keywordDensity: Math.max(0, keywordDensity),
    responseTime: 1.0, // Will be adjusted externally
    structureScore,
  }
}

export function calculateRoundScore(
  userMessage: Message,
  aiMessage: Message,
  mode: DebateMode,
  responseTimeSeconds: number,
  timerDuration: number
): { userScore: number; aiScore: number } {
  const userFactors = analyzeArgument(userMessage.content)
  const aiFactors = analyzeArgument(aiMessage.content)
  
  // Response time scoring (faster is better, but not too fast)
  const timeRatio = responseTimeSeconds / timerDuration
  if (timeRatio < 0.1) {
    userFactors.responseTime = 0.7 // Too fast, probably not thoughtful
  } else if (timeRatio < 0.5) {
    userFactors.responseTime = 1.0 // Good pace
  } else if (timeRatio < 0.8) {
    userFactors.responseTime = 0.85 // Acceptable
  } else {
    userFactors.responseTime = 0.7 // Rushed at the end
  }
  
  // Calculate base scores
  const userBase = (
    userFactors.argumentLength * 0.3 +
    userFactors.keywordDensity * 0.35 +
    userFactors.responseTime * 0.15 +
    userFactors.structureScore * 0.2
  )
  
  const aiBase = (
    aiFactors.argumentLength * 0.3 +
    aiFactors.keywordDensity * 0.35 +
    aiFactors.structureScore * 0.35
  )
  
  // Mode difficulty adjustments
  const modeMultiplier = {
    casual: 1.2,    // User gets bonus
    balanced: 1.0,  // Fair
    intense: 0.85,  // AI gets slight edge
  }
  
  const adjustedUserScore = userBase * modeMultiplier[mode]
  
  // Determine points (0-3 scale per round)
  let userPoints: number
  let aiPoints: number
  
  const scoreDiff = adjustedUserScore - aiBase
  
  if (scoreDiff > 0.2) {
    userPoints = 3
    aiPoints = 1
  } else if (scoreDiff > 0.05) {
    userPoints = 2
    aiPoints = 1
  } else if (scoreDiff > -0.05) {
    userPoints = 2
    aiPoints = 2
  } else if (scoreDiff > -0.2) {
    userPoints = 1
    aiPoints = 2
  } else {
    userPoints = 1
    aiPoints = 3
  }
  
  return { userScore: userPoints, aiScore: aiPoints }
}

export function determineRoundWinner(
  userScore: number,
  aiScore: number
): 'user' | 'ai' | 'tie' {
  if (userScore > aiScore) return 'user'
  if (aiScore > userScore) return 'ai'
  return 'tie'
}

export function calculateFinalVerdict(
  rounds: Round[]
): { winner: 'user' | 'ai' | 'tie'; totalUser: number; totalAi: number } {
  const totalUser = rounds.reduce((sum, r) => sum + r.userScore, 0)
  const totalAi = rounds.reduce((sum, r) => sum + r.aiScore, 0)
  
  let winner: 'user' | 'ai' | 'tie'
  if (totalUser > totalAi) {
    winner = 'user'
  } else if (totalAi > totalUser) {
    winner = 'ai'
  } else {
    // Tiebreaker: who won more rounds
    const userWins = rounds.filter((r) => r.winner === 'user').length
    const aiWins = rounds.filter((r) => r.winner === 'ai').length
    winner = userWins > aiWins ? 'user' : aiWins > userWins ? 'ai' : 'tie'
  }
  
  return { winner, totalUser, totalAi }
}

export function getAverageResponseTime(rounds: Round[]): number {
  if (rounds.length === 0) return 0
  const total = rounds.reduce((sum, r) => sum + r.duration, 0)
  return Math.round(total / rounds.length)
}

export function getStrongestRound(rounds: Round[]): number {
  if (rounds.length === 0) return 0
  let strongest = rounds[0]
  for (const round of rounds) {
    const currentDiff = round.userScore - round.aiScore
    const strongestDiff = strongest.userScore - strongest.aiScore
    if (currentDiff > strongestDiff) {
      strongest = round
    }
  }
  return strongest.number
}

export function getWeakestRound(rounds: Round[]): number {
  if (rounds.length === 0) return 0
  let weakest = rounds[0]
  for (const round of rounds) {
    const currentDiff = round.userScore - round.aiScore
    const weakestDiff = weakest.userScore - weakest.aiScore
    if (currentDiff < weakestDiff) {
      weakest = round
    }
  }
  return weakest.number
}
