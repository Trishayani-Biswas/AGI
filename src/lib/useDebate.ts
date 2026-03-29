import { useState, useCallback, useRef } from 'react'
import type { DebateSession, Message, Round, DebateMode, Side, Verdict } from './types'
import { generateId, saveSession } from './storage'
import { calculateRoundScore, determineRoundWinner, calculateFinalVerdict } from './scoring'
import { callAnthropicAPI, callDebateBackend, getDebateVerdict, getMockAIResponse } from './backendClient'

interface UseDebateOptions {
  apiKey: string | null
  backendUrl?: string | null
  totalRounds?: number
  onRoundEnd?: (round: Round) => void
  onDebateEnd?: (verdict: Verdict) => void
}

interface UseDebateReturn {
  session: DebateSession | null
  currentRound: number
  isAiThinking: boolean
  startDebate: (topic: string, mode: DebateMode, side: Side, timerDuration: number) => void
  sendMessage: (content: string, responseTime: number, timerDuration: number) => Promise<void>
  endRound: () => void
  endDebate: () => Promise<void>
  resetDebate: () => void
}

const MAX_MESSAGE_LENGTH = 1200

const validateOutgoingMessage = (content: string): string => {
  const trimmed = content.trim()
  if (!trimmed) {
    throw new Error('Message cannot be empty.')
  }
  if (trimmed.length > MAX_MESSAGE_LENGTH) {
    throw new Error(`Message is too long. Keep it under ${MAX_MESSAGE_LENGTH} characters.`)
  }
  return trimmed
}

export function useDebate({
  apiKey,
  backendUrl,
  totalRounds = 5,
  onRoundEnd,
  onDebateEnd,
}: UseDebateOptions): UseDebateReturn {
  const [session, setSession] = useState<DebateSession | null>(null)
  const [currentRound, setCurrentRound] = useState(1)
  const [isAiThinking, setIsAiThinking] = useState(false)
  const roundMessagesRef = useRef<Message[]>([])
  const roundCompletedRef = useRef<Set<number>>(new Set())

  const startDebate = useCallback((
    topic: string,
    mode: DebateMode,
    side: Side,
    timerDuration: number
  ) => {
    void timerDuration
    const newSession: DebateSession = {
      id: generateId(),
      topic,
      mode,
      side,
      messages: [],
      rounds: [],
      totalUserScore: 0,
      totalAiScore: 0,
      createdAt: Date.now(),
    }
    setSession(newSession)
    setCurrentRound(1)
    roundMessagesRef.current = []
    roundCompletedRef.current.clear()
  }, [])

  const sendMessage = useCallback(async (
    content: string,
    responseTime: number,
    timerDuration: number
  ) => {
    if (!session) return
    if (isAiThinking) throw new Error('Please wait for FlipSide to respond before sending another message.')
    const safeContent = validateOutgoingMessage(content)
    const targetRound = currentRound
    if (roundCompletedRef.current.has(targetRound)) {
      throw new Error('This round is already complete. Please continue to the next round.')
    }

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: safeContent,
      timestamp: Date.now(),
      roundNumber: targetRound,
    }

    setSession((prev) => prev ? {
      ...prev,
      messages: [...prev.messages, userMessage],
    } : null)
    roundMessagesRef.current.push(userMessage)

    setIsAiThinking(true)

    try {
      let aiContent: string

      const allMessages = [...session.messages, userMessage]
      const envBackendUrl = (import.meta.env.VITE_BACKEND_URL as string | undefined)?.trim()
      const backendBaseUrl = (backendUrl || envBackendUrl || '').trim()

      if (backendBaseUrl) {
        aiContent = await callDebateBackend(
          backendBaseUrl,
          {
            topic: session.topic,
              mode: session.mode,
              userSide: session.side,
              roundNumber: targetRound,
              totalRounds,
              messages: allMessages,
            },
          apiKey ?? undefined
        )
      } else if (apiKey) {
        aiContent = await callAnthropicAPI(
          apiKey,
          allMessages,
          session.mode,
          session.topic,
          session.side,
          targetRound,
          totalRounds
        )
      } else {
        await new Promise((resolve) => setTimeout(resolve, 800))
        aiContent = getMockAIResponse(
          allMessages,
          session.mode,
          session.topic,
          session.side
        )
      }

      const aiMessage: Message = {
        id: generateId(),
        role: 'ai',
        content: aiContent,
        timestamp: Date.now(),
        roundNumber: targetRound,
      }

      roundMessagesRef.current.push(aiMessage)

      // Calculate scores for this exchange
      const { userScore, aiScore } = calculateRoundScore(
        userMessage,
        aiMessage,
        session.mode,
        responseTime,
        timerDuration
      )

      if (roundCompletedRef.current.has(targetRound)) {
        return
      }

      setSession((prev) => {
        if (!prev) return null
        if (roundCompletedRef.current.has(targetRound)) return prev
        
        const updatedMessages = [...prev.messages, aiMessage]
        
        // Check if round should end (after one exchange per round)
        const roundComplete = roundMessagesRef.current.length >= 2 && !prev.rounds.some((round) => round.number === targetRound)
        
        if (roundComplete) {
          const round: Round = {
            number: targetRound,
            winner: determineRoundWinner(userScore, aiScore),
            userScore,
            aiScore,
            duration: responseTime,
          }
          
          const updatedRounds = [...prev.rounds, round]
          const newTotalUser = prev.totalUserScore + userScore
          const newTotalAi = prev.totalAiScore + aiScore

          roundCompletedRef.current.add(targetRound)
          onRoundEnd?.(round)

          return {
            ...prev,
            messages: updatedMessages,
            rounds: updatedRounds,
            totalUserScore: newTotalUser,
            totalAiScore: newTotalAi,
          }
        }

        return {
          ...prev,
          messages: updatedMessages,
        }
      })
    } catch (error) {
      console.error('Error getting AI response:', error)
      // Create a fallback response
      const fallbackMessage: Message = {
        id: generateId(),
        role: 'ai',
        content: 'I apologize, but I encountered an issue processing your argument. Please try again.',
        timestamp: Date.now(),
        roundNumber: targetRound,
      }
      const { userScore, aiScore } = calculateRoundScore(
        userMessage,
        fallbackMessage,
        session.mode,
        responseTime,
        timerDuration
      )
      setSession((prev) => {
        if (!prev) return null
        if (prev.rounds.some((round) => round.number === targetRound)) return prev

        const round: Round = {
          number: targetRound,
          winner: determineRoundWinner(userScore, aiScore),
          userScore,
          aiScore,
          duration: responseTime,
        }
        roundCompletedRef.current.add(targetRound)
        onRoundEnd?.(round)

        return {
          ...prev,
          messages: [...prev.messages, fallbackMessage],
          rounds: [...prev.rounds, round],
          totalUserScore: prev.totalUserScore + userScore,
          totalAiScore: prev.totalAiScore + aiScore,
        }
      })
    } finally {
      setIsAiThinking(false)
    }
  }, [session, currentRound, apiKey, totalRounds, onRoundEnd, isAiThinking, backendUrl])

  const endRound = useCallback(() => {
    roundCompletedRef.current.add(currentRound)
    setCurrentRound((prev) => prev + 1)
    roundMessagesRef.current = []
  }, [currentRound])

  const endDebate = useCallback(async () => {
    if (!session) return

    let verdict: Verdict

    if (apiKey) {
      try {
        verdict = await getDebateVerdict(
          apiKey,
          session.topic,
          session.side,
          session.totalUserScore,
          session.totalAiScore,
          session.messages
        )
      } catch {
        const { winner } = calculateFinalVerdict(session.rounds)
        verdict = {
          winner,
          summary: winner === 'user' 
            ? 'Congratulations! You won the debate with strong arguments.'
            : winner === 'ai'
            ? 'FlipSide won this debate. Great effort though!'
            : 'The debate ended in a tie. Well matched!',
          strengths: ['Consistent argumentation'],
          weaknesses: ['Could provide more evidence'],
          overallAnalysis: 'Thank you for participating in this debate.',
        }
      }
    } else {
      const { winner } = calculateFinalVerdict(session.rounds)
      verdict = {
        winner,
        summary: winner === 'user' 
          ? 'Congratulations! You won the debate with strong arguments.'
          : winner === 'ai'
          ? 'FlipSide won this debate. Great effort though!'
          : 'The debate ended in a tie. Well matched!',
        strengths: ['Good engagement', 'Clear points made'],
        weaknesses: ['Room for more evidence'],
        overallAnalysis: 'A well-fought debate on both sides.',
      }
    }

    const completedSession: DebateSession = {
      ...session,
      verdict,
      completedAt: Date.now(),
    }

    setSession(completedSession)
    saveSession(completedSession)
    onDebateEnd?.(verdict)
  }, [session, apiKey, onDebateEnd])

  const resetDebate = useCallback(() => {
    setSession(null)
    setCurrentRound(1)
    setIsAiThinking(false)
    roundMessagesRef.current = []
    roundCompletedRef.current.clear()
  }, [])

  return {
    session,
    currentRound,
    isAiThinking,
    startDebate,
    sendMessage,
    endRound,
    endDebate,
    resetDebate,
  }
}
