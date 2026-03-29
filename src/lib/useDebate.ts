import { useState, useCallback, useRef } from 'react'
import type { DebateSession, Message, Round, DebateMode, Side, Verdict } from './types'
import { generateId, saveSession } from './storage'
import { calculateRoundScore, determineRoundWinner, calculateFinalVerdict } from './scoring'
import { callAnthropicAPI, getDebateVerdict, getMockAIResponse } from './backendClient'

interface UseDebateOptions {
  apiKey: string | null
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

export function useDebate({
  apiKey,
  totalRounds = 5,
  onRoundEnd,
  onDebateEnd,
}: UseDebateOptions): UseDebateReturn {
  const [session, setSession] = useState<DebateSession | null>(null)
  const [currentRound, setCurrentRound] = useState(1)
  const [isAiThinking, setIsAiThinking] = useState(false)
  const roundMessagesRef = useRef<Message[]>([])

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
  }, [])

  const sendMessage = useCallback(async (
    content: string,
    responseTime: number,
    timerDuration: number
  ) => {
    if (!session) return

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: Date.now(),
      roundNumber: currentRound,
    }

    setSession((prev) => prev ? {
      ...prev,
      messages: [...prev.messages, userMessage],
    } : null)
    roundMessagesRef.current.push(userMessage)

    setIsAiThinking(true)

    try {
      let aiContent: string

      if (apiKey) {
        aiContent = await callAnthropicAPI(
          apiKey,
          [...session.messages, userMessage],
          session.mode,
          session.topic,
          session.side,
          currentRound,
          totalRounds
        )
      } else {
        // Simulate thinking delay for mock
        await new Promise((resolve) => setTimeout(resolve, 1500))
        aiContent = getMockAIResponse(
          [...session.messages, userMessage],
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
        roundNumber: currentRound,
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

      setSession((prev) => {
        if (!prev) return null
        
        const updatedMessages = [...prev.messages, aiMessage]
        
        // Check if round should end (after one exchange per round)
        const roundComplete = roundMessagesRef.current.length >= 2
        
        if (roundComplete) {
          const round: Round = {
            number: currentRound,
            winner: determineRoundWinner(userScore, aiScore),
            userScore,
            aiScore,
            duration: responseTime,
          }
          
          const updatedRounds = [...prev.rounds, round]
          const newTotalUser = prev.totalUserScore + userScore
          const newTotalAi = prev.totalAiScore + aiScore

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
        roundNumber: currentRound,
      }
      setSession((prev) => prev ? {
        ...prev,
        messages: [...prev.messages, fallbackMessage],
      } : null)
    } finally {
      setIsAiThinking(false)
    }
  }, [session, currentRound, apiKey, totalRounds, onRoundEnd])

  const endRound = useCallback(() => {
    setCurrentRound((prev) => prev + 1)
    roundMessagesRef.current = []
  }, [])

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
