/**
 * FlipSide 2.0 Project Setup Script
 * 
 * Run this script to create all necessary directories and files for the
 * FlipSide application with the new modular architecture.
 * 
 * Usage: node setup-project.mjs
 */

import { mkdir, writeFile } from 'fs/promises';
import { join } from 'path';

const ROOT = process.cwd();
const SRC = join(ROOT, 'src');

// Directories to create
const directories = [
  'src/types',
  'src/hooks',
  'src/test',
  'src/components/setup',
  'src/components/debate',
  'src/components/stats',
  'src/components/ui',
  'src/screens',
];

// Files to create
const files = {
  // Types
  'src/types/index.ts': `export type DebateMode = 'casual' | 'balanced' | 'intense'

export type Side = 'for' | 'against'

export type MessageRole = 'user' | 'ai'

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: number
  roundNumber: number
}

export interface Round {
  number: number
  winner: 'user' | 'ai' | 'tie'
  userScore: number
  aiScore: number
  duration: number
}

export interface Verdict {
  winner: 'user' | 'ai' | 'tie'
  summary: string
  strengths: string[]
  weaknesses: string[]
  overallAnalysis: string
}

export interface DebateSession {
  id: string
  topic: string
  mode: DebateMode
  side: Side
  messages: Message[]
  rounds: Round[]
  totalUserScore: number
  totalAiScore: number
  createdAt: number
  completedAt?: number
  verdict?: Verdict
}

export interface Player {
  id: string
  name: string
  avatarInitial: string
}

export interface AppSettings {
  apiKey: string
  defaultMode: DebateMode
  defaultTimer: number
  coachEnabled: boolean
}

export interface ToastMessage {
  id: string
  type: 'success' | 'error' | 'info'
  message: string
  duration?: number
}

export interface CoachTip {
  id: string
  content: string
  category: 'structure' | 'evidence' | 'rebuttal' | 'clarity'
}

export type Screen = 'setup' | 'debate' | 'stats'

export interface DebateState {
  session: DebateSession | null
  currentRound: number
  isAiThinking: boolean
  timerActive: boolean
  timeRemaining: number
}
`,

  // Test setup
  'src/test/setup.ts': `import '@testing-library/jest-dom'
`,

  // Hooks
  'src/hooks/useLocalStorage.ts': `import { useState, useEffect, useCallback } from 'react'

export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key)
      return item ? (JSON.parse(item) as T) : initialValue
    } catch (error) {
      console.error(\`Error reading localStorage key "\${key}":\`, error)
      return initialValue
    }
  })

  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      window.localStorage.setItem(key, JSON.stringify(valueToStore))
    } catch (error) {
      console.error(\`Error setting localStorage key "\${key}":\`, error)
    }
  }, [key, storedValue])

  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === key && e.newValue) {
        try {
          setStoredValue(JSON.parse(e.newValue) as T)
        } catch {
          // Ignore parse errors
        }
      }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [key])

  return [storedValue, setValue]
}
`,

  'src/hooks/useTimer.ts': `import { useState, useEffect, useCallback, useRef } from 'react'

interface UseTimerOptions {
  initialTime: number
  onComplete?: () => void
  autoStart?: boolean
}

interface UseTimerReturn {
  timeRemaining: number
  isRunning: boolean
  isComplete: boolean
  start: () => void
  pause: () => void
  reset: (newTime?: number) => void
  percentRemaining: number
}

export function useTimer({
  initialTime,
  onComplete,
  autoStart = false,
}: UseTimerOptions): UseTimerReturn {
  const [timeRemaining, setTimeRemaining] = useState(initialTime)
  const [isRunning, setIsRunning] = useState(autoStart)
  const [isComplete, setIsComplete] = useState(false)
  const onCompleteRef = useRef(onComplete)
  
  useEffect(() => {
    onCompleteRef.current = onComplete
  }, [onComplete])

  useEffect(() => {
    if (!isRunning || timeRemaining <= 0) return

    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          setIsRunning(false)
          setIsComplete(true)
          onCompleteRef.current?.()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [isRunning, timeRemaining])

  const start = useCallback(() => {
    if (timeRemaining > 0) {
      setIsRunning(true)
      setIsComplete(false)
    }
  }, [timeRemaining])

  const pause = useCallback(() => {
    setIsRunning(false)
  }, [])

  const reset = useCallback((newTime?: number) => {
    setTimeRemaining(newTime ?? initialTime)
    setIsRunning(false)
    setIsComplete(false)
  }, [initialTime])

  const percentRemaining = (timeRemaining / initialTime) * 100

  return {
    timeRemaining,
    isRunning,
    isComplete,
    start,
    pause,
    reset,
    percentRemaining,
  }
}
`,

  'src/hooks/useToast.ts': `import { useState, useCallback } from 'react'
import type { ToastMessage } from '@/types'
import { generateId } from '@/lib/storage'

interface UseToastReturn {
  toasts: ToastMessage[]
  addToast: (type: ToastMessage['type'], message: string, duration?: number) => void
  removeToast: (id: string) => void
  clearAll: () => void
}

const MAX_TOASTS = 3
const DEFAULT_DURATION = 3000

export function useToast(): UseToastReturn {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback((
    type: ToastMessage['type'],
    message: string,
    duration: number = DEFAULT_DURATION
  ) => {
    const id = generateId()
    const newToast: ToastMessage = { id, type, message, duration }

    setToasts((prev) => {
      const updated = [newToast, ...prev].slice(0, MAX_TOASTS)
      return updated
    })

    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
  }, [removeToast])

  const clearAll = useCallback(() => {
    setToasts([])
  }, [])

  return { toasts, addToast, removeToast, clearAll }
}
`,

  'src/hooks/useDebate.ts': `import { useState, useCallback, useRef } from 'react'
import type { DebateSession, Message, Round, DebateMode, Side, Verdict } from '@/types'
import { generateId, saveSession } from '@/lib/storage'
import { calculateRoundScore, determineRoundWinner, calculateFinalVerdict } from '@/lib/scoring'
import { callAnthropicAPI, getDebateVerdict, getMockAIResponse } from '@/lib/backendClient'

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
    _timerDuration: number
  ) => {
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
`,

  // UI Components
  'src/components/ui/Button.tsx': `import { forwardRef, type ButtonHTMLAttributes, type ReactNode, useRef, useCallback } from 'react'
import { motion, type HTMLMotionProps } from 'framer-motion'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'ref'> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  fullWidth?: boolean
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-gold-primary text-background hover:bg-gold-primary/90 shine-effect',
  secondary: 'bg-surface-raised text-text-primary hover:bg-surface-raised/80 border border-border',
  outline: 'bg-transparent text-gold-primary border border-gold-primary hover:bg-gold-glow',
  ghost: 'bg-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised',
}

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2.5',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({
  className,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  fullWidth = false,
  disabled,
  children,
  onClick,
  ...props
}, ref) => {
  const buttonRef = useRef<HTMLButtonElement | null>(null)

  const handleClick = useCallback((e: React.MouseEvent<HTMLButtonElement>) => {
    if (disabled || isLoading) return

    // Create ripple effect
    const button = buttonRef.current
    if (button) {
      const rect = button.getBoundingClientRect()
      const ripple = document.createElement('span')
      const size = Math.max(rect.width, rect.height)
      
      ripple.style.width = ripple.style.height = size + 'px'
      ripple.style.left = e.clientX - rect.left - size / 2 + 'px'
      ripple.style.top = e.clientY - rect.top - size / 2 + 'px'
      ripple.className = 'ripple'
      
      button.appendChild(ripple)
      setTimeout(() => ripple.remove(), 400)
    }

    onClick?.(e)
  }, [disabled, isLoading, onClick])

  const setRefs = useCallback((node: HTMLButtonElement | null) => {
    buttonRef.current = node
    if (typeof ref === 'function') {
      ref(node)
    } else if (ref) {
      ref.current = node
    }
  }, [ref])

  return (
    <motion.button
      ref={setRefs}
      className={twMerge(clsx(
        'relative inline-flex items-center justify-center font-semibold rounded-button',
        'transition-colors duration-200 focus-ring ripple-effect overflow-hidden',
        variantStyles[variant],
        sizeStyles[size],
        fullWidth && 'w-full',
        (disabled || isLoading) && 'opacity-50 cursor-not-allowed',
        className
      ))}
      disabled={disabled || isLoading}
      whileTap={{ scale: disabled || isLoading ? 1 : 0.97 }}
      transition={{ duration: 0.1 }}
      onClick={handleClick}
      {...props}
    >
      {isLoading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        <>
          {leftIcon && <span className="flex-shrink-0">{leftIcon}</span>}
          {children}
          {rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
        </>
      )}
    </motion.button>
  )
})

Button.displayName = 'Button'
`,

  'src/components/ui/Pill.tsx': `import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

interface PillProps {
  children: ReactNode
  isSelected?: boolean
  onClick?: () => void
  size?: 'sm' | 'md'
  className?: string
  disabled?: boolean
}

export function Pill({
  children,
  isSelected = false,
  onClick,
  size = 'md',
  className,
  disabled = false,
}: PillProps) {
  const sizeStyles = {
    sm: 'px-2.5 py-1 text-xs',
    md: 'px-4 py-2 text-sm',
  }

  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={twMerge(clsx(
        'rounded-pill font-medium transition-all duration-200 focus-ring',
        sizeStyles[size],
        isSelected
          ? 'bg-gold-primary text-background'
          : 'bg-surface-raised text-text-secondary hover:text-text-primary hover:border-gold-primary/30',
        'border',
        isSelected ? 'border-gold-primary' : 'border-border',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      ))}
      whileTap={{ scale: disabled ? 1 : 0.97 }}
      transition={{ duration: 0.1 }}
    >
      {children}
    </motion.button>
  )
}
`,

  'src/components/ui/AvatarChip.tsx': `import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

interface AvatarChipProps {
  initial: string
  name?: string
  size?: 'sm' | 'md' | 'lg'
  variant?: 'gold' | 'surface'
  showName?: boolean
  className?: string
}

export function AvatarChip({
  initial,
  name,
  size = 'md',
  variant = 'gold',
  showName = true,
  className,
}: AvatarChipProps) {
  const sizeStyles = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-10 h-10 text-base',
  }

  const variantStyles = {
    gold: 'bg-gold-primary text-background',
    surface: 'bg-surface-raised text-text-secondary border border-border',
  }

  return (
    <div className={twMerge(clsx('inline-flex items-center gap-2', className))}>
      <span
        className={clsx(
          'flex items-center justify-center rounded-full font-semibold uppercase',
          sizeStyles[size],
          variantStyles[variant]
        )}
        aria-hidden="true"
      >
        {initial}
      </span>
      {showName && name && (
        <span className="text-sm text-text-primary font-medium">{name}</span>
      )}
    </div>
  )
}
`,

  'src/components/ui/Modal.tsx': `import { type ReactNode, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { clsx } from 'clsx'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  className?: string
  showCloseButton?: boolean
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  className,
  showCloseButton = true,
}: ModalProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }, [onClose])

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleKeyDown])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-hidden="true"
          />
          
          {/* Modal */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className={clsx(
                'glass-surface rounded-card shadow-card w-full max-w-md p-6',
                className
              )}
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-labelledby={title ? 'modal-title' : undefined}
            >
              {(title || showCloseButton) && (
                <div className="flex items-center justify-between mb-4">
                  {title && (
                    <h2 id="modal-title" className="text-h2 text-text-primary">
                      {title}
                    </h2>
                  )}
                  {showCloseButton && (
                    <button
                      onClick={onClose}
                      className="p-1 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors focus-ring"
                      aria-label="Close modal"
                    >
                      <X size={20} />
                    </button>
                  )}
                </div>
              )}
              {children}
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
`,

  'src/components/ui/Toast.tsx': `import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'
import type { ToastMessage } from '@/types'
import { clsx } from 'clsx'

interface ToastContainerProps {
  toasts: ToastMessage[]
  onRemove: (id: string) => void
}

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
}

const colorMap = {
  success: 'border-success/50 text-success',
  error: 'border-error/50 text-error',
  info: 'border-gold-primary/50 text-gold-primary',
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => {
          const Icon = iconMap[toast.type]
          
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={clsx(
                'glass-surface rounded-card px-4 py-3 shadow-card pointer-events-auto',
                'flex items-center gap-3 min-w-[280px] max-w-md',
                'border',
                colorMap[toast.type]
              )}
            >
              <Icon size={18} className="flex-shrink-0" />
              <p className="text-sm text-text-primary flex-grow">{toast.message}</p>
              <button
                onClick={() => onRemove(toast.id)}
                className="p-0.5 rounded text-text-secondary hover:text-text-primary transition-colors"
                aria-label="Dismiss"
              >
                <X size={16} />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
`,

  'src/components/ui/Skeleton.tsx': `import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
  width?: string | number
  height?: string | number
}

export function Skeleton({
  className,
  variant = 'rectangular',
  width,
  height,
}: SkeletonProps) {
  const variantStyles = {
    text: 'rounded h-4',
    circular: 'rounded-full',
    rectangular: 'rounded-input',
  }

  return (
    <div
      className={clsx('skeleton', variantStyles[variant], className)}
      style={{ width, height }}
      aria-hidden="true"
    />
  )
}

export function MessageSkeleton() {
  return (
    <div className="flex gap-3 animate-pulse">
      <Skeleton variant="circular" width={32} height={32} />
      <div className="flex-1 space-y-2">
        <Skeleton width="40%" height={16} />
        <Skeleton width="80%" height={16} />
        <Skeleton width="60%" height={16} />
      </div>
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-surface rounded-card p-4 space-y-3 animate-pulse">
      <Skeleton width="60%" height={20} />
      <Skeleton width="100%" height={14} />
      <Skeleton width="80%" height={14} />
    </div>
  )
}
`,

  'src/components/ui/EmptyState.tsx': `import { type ReactNode } from 'react'
import { clsx } from 'clsx'
import { Button } from './Button'

interface EmptyStateProps {
  icon: ReactNode
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={clsx('flex flex-col items-center justify-center py-12 px-4 text-center', className)}>
      <div className="text-text-disabled mb-4" aria-hidden="true">
        {icon}
      </div>
      <h3 className="text-h3 text-text-secondary mb-1">{title}</h3>
      {description && (
        <p className="text-body text-text-disabled mb-4 max-w-xs">{description}</p>
      )}
      {action && (
        <Button variant="outline" size="sm" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  )
}
`,

  // Setup Components
  'src/components/setup/TopicInput.tsx': `import { useState } from 'react'
import { clsx } from 'clsx'

interface TopicInputProps {
  value: string
  onChange: (value: string) => void
  maxLength?: number
  error?: string
}

export function TopicInput({
  value,
  onChange,
  maxLength = 200,
  error,
}: TopicInputProps) {
  const [isFocused, setIsFocused] = useState(false)
  const charCount = value.length
  const isNearLimit = charCount > maxLength * 0.8

  return (
    <div className="space-y-1.5">
      <label
        htmlFor="topic-input"
        className="text-label text-text-secondary"
      >
        Debate Topic
      </label>
      
      <div className="relative">
        <input
          id="topic-input"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value.slice(0, maxLength))}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="e.g. AI will replace creative jobs"
          className={clsx(
            'w-full px-4 py-3 rounded-input bg-surface-raised border text-text-primary',
            'placeholder:text-text-disabled transition-all duration-200 focus-ring',
            error
              ? 'border-error'
              : isFocused
              ? 'border-gold-primary'
              : 'border-border hover:border-border/80'
          )}
          aria-describedby={error ? 'topic-error' : 'topic-hint'}
        />
        
        <span
          className={clsx(
            'absolute right-3 top-1/2 -translate-y-1/2 text-caption',
            isNearLimit ? 'text-error' : 'text-text-disabled'
          )}
        >
          {charCount}/{maxLength}
        </span>
      </div>
      
      {error && (
        <p id="topic-error" className="text-caption text-error">
          {error}
        </p>
      )}
    </div>
  )
}
`,

  'src/components/setup/TopicList.tsx': `import { motion } from 'framer-motion'
import { clsx } from 'clsx'

interface TopicListProps {
  onSelect: (topic: string) => void
  selectedTopic?: string
}

const PRESET_TOPICS = [
  'AI in Governance',
  'UBI vs Meritocracy',
  'Space > Earth Problems?',
  'Social Media is Toxic',
]

export function TopicList({ onSelect, selectedTopic }: TopicListProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2 -mx-2 px-2 scrollbar-hide">
      {PRESET_TOPICS.map((topic, index) => (
        <motion.button
          key={topic}
          type="button"
          onClick={() => onSelect(topic)}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
          className={clsx(
            'flex-shrink-0 px-3 py-1.5 rounded-pill text-caption font-medium',
            'border transition-all duration-200 focus-ring',
            selectedTopic === topic
              ? 'bg-gold-glow border-gold-primary text-gold-primary'
              : 'bg-surface-raised border-border text-text-secondary hover:text-text-primary hover:border-gold-primary/30'
          )}
        >
          {topic}
        </motion.button>
      ))}
    </div>
  )
}
`,

  'src/components/setup/ModePills.tsx': `import { Pill } from '@/components/ui/Pill'
import type { DebateMode } from '@/types'

interface ModePillsProps {
  value: DebateMode
  onChange: (mode: DebateMode) => void
}

const MODES: { value: DebateMode; label: string }[] = [
  { value: 'casual', label: 'Casual' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'intense', label: 'Intense' },
]

export function ModePills({ value, onChange }: ModePillsProps) {
  return (
    <div className="space-y-1.5">
      <span className="text-label text-text-secondary">Difficulty</span>
      <div className="flex gap-2">
        {MODES.map((mode) => (
          <Pill
            key={mode.value}
            isSelected={value === mode.value}
            onClick={() => onChange(mode.value)}
          >
            {mode.label}
          </Pill>
        ))}
      </div>
    </div>
  )
}
`,

  'src/components/setup/SideSelector.tsx': `import { motion } from 'framer-motion'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import type { Side } from '@/types'
import { clsx } from 'clsx'

interface SideSelectorProps {
  value: Side
  onChange: (side: Side) => void
}

export function SideSelector({ value, onChange }: SideSelectorProps) {
  return (
    <div className="space-y-1.5">
      <span className="text-label text-text-secondary">Your Side</span>
      <div className="grid grid-cols-2 gap-3">
        <SideCard
          side="for"
          isSelected={value === 'for'}
          onClick={() => onChange('for')}
          icon={<ThumbsUp size={24} />}
          label="FOR"
        />
        <SideCard
          side="against"
          isSelected={value === 'against'}
          onClick={() => onChange('against')}
          icon={<ThumbsDown size={24} />}
          label="AGAINST"
        />
      </div>
    </div>
  )
}

interface SideCardProps {
  side: Side
  isSelected: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}

function SideCard({ isSelected, onClick, icon, label }: SideCardProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      className={clsx(
        'relative h-20 rounded-card border flex flex-col items-center justify-center gap-2',
        'transition-all duration-200 focus-ring overflow-hidden',
        isSelected
          ? 'bg-gold-glow border-gold-primary text-gold-primary shadow-inner-glow'
          : 'bg-surface-raised border-border text-text-secondary hover:text-text-primary hover:border-border/80'
      )}
      whileTap={{ scale: 0.98 }}
    >
      {isSelected && (
        <motion.div
          className="absolute inset-0 bg-gold-glow"
          layoutId="side-selector-bg"
          transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
        />
      )}
      <span className="relative z-10">{icon}</span>
      <span className="relative z-10 text-label font-bold">{label}</span>
    </motion.button>
  )
}
`,

  'src/components/setup/TimerSelect.tsx': `import { Pill } from '@/components/ui/Pill'

interface TimerSelectProps {
  value: number
  onChange: (seconds: number) => void
}

const TIMER_OPTIONS = [
  { value: 180, label: '3 min' },
  { value: 120, label: '2 min' },
  { value: 90, label: '90 sec' },
]

export function TimerSelect({ value, onChange }: TimerSelectProps) {
  return (
    <div className="space-y-1.5">
      <span className="text-label text-text-secondary">Round Timer</span>
      <div className="flex gap-2">
        {TIMER_OPTIONS.map((option) => (
          <Pill
            key={option.value}
            isSelected={value === option.value}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </Pill>
        ))}
      </div>
    </div>
  )
}
`,

  'src/components/setup/SetupCard.tsx': `import { type ReactNode } from 'react'
import { motion } from 'framer-motion'

interface SetupCardProps {
  children: ReactNode
}

export function SetupCard({ children }: SetupCardProps) {
  return (
    <motion.div
      className="glass-surface rounded-card shadow-card p-6 space-y-6"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  )
}
`,

  'src/components/setup/HistoryPanel.tsx': `import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Clock, ChevronDown, Trash2, History } from 'lucide-react'
import type { DebateSession } from '@/types'
import { Pill } from '@/components/ui/Pill'
import { EmptyState } from '@/components/ui/EmptyState'
import { clsx } from 'clsx'

interface HistoryPanelProps {
  sessions: DebateSession[]
  onSelect: (session: DebateSession) => void
  onDelete: (sessionId: string) => void
}

export function HistoryPanel({ sessions, onSelect, onDelete }: HistoryPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 rounded-card bg-surface-raised border border-border hover:border-border/80 transition-colors focus-ring"
      >
        <div className="flex items-center gap-2 text-text-secondary">
          <Clock size={16} />
          <span className="text-sm font-medium">Past Debates</span>
          {sessions.length > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-gold-glow text-gold-primary text-xs font-medium">
              {sessions.length}
            </span>
          )}
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown size={16} className="text-text-disabled" />
        </motion.div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pt-2 max-h-64 overflow-y-auto space-y-2">
              {sessions.length === 0 ? (
                <EmptyState
                  icon={<History size={32} />}
                  title="No debates yet"
                  description="Start your first debate to see it here"
                />
              ) : (
                sessions.map((session) => (
                  <HistoryRow
                    key={session.id}
                    session={session}
                    onClick={() => onSelect(session)}
                    onDelete={() => onDelete(session.id)}
                  />
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

interface HistoryRowProps {
  session: DebateSession
  onClick: () => void
  onDelete: () => void
}

function HistoryRow({ session, onClick, onDelete }: HistoryRowProps) {
  const date = new Date(session.createdAt).toLocaleDateString()
  const winner = session.verdict?.winner

  return (
    <motion.div
      className="group flex items-center gap-3 p-3 rounded-card bg-surface border border-border hover:border-border/80 cursor-pointer transition-colors"
      onClick={onClick}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary truncate">{session.topic}</p>
        <div className="flex items-center gap-2 mt-1">
          <Pill size="sm" className="capitalize text-[10px] py-0.5 px-1.5">
            {session.mode}
          </Pill>
          <span className="text-caption text-text-disabled">{date}</span>
        </div>
      </div>

      {winner && (
        <span
          className={clsx(
            'text-xs font-semibold px-2 py-1 rounded',
            winner === 'user' && 'bg-success/20 text-success',
            winner === 'ai' && 'bg-error/20 text-error',
            winner === 'tie' && 'bg-gold-glow text-gold-primary'
          )}
        >
          {winner === 'user' ? 'Won' : winner === 'ai' ? 'Lost' : 'Tie'}
        </span>
      )}

      <button
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        className="p-1.5 rounded opacity-0 group-hover:opacity-100 text-text-disabled hover:text-error hover:bg-error/10 transition-all focus-ring"
        aria-label="Delete debate"
      >
        <Trash2 size={14} />
      </button>
    </motion.div>
  )
}
`,

  'src/components/setup/MultiplayerControls.tsx': `import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Users, ChevronDown, Plus, X } from 'lucide-react'
import type { Player } from '@/types'
import { Button } from '@/components/ui/Button'
import { AvatarChip } from '@/components/ui/AvatarChip'
import { generateId } from '@/lib/storage'

interface MultiplayerControlsProps {
  players: Player[]
  onPlayersChange: (players: Player[]) => void
  maxPlayers?: number
}

export function MultiplayerControls({
  players,
  onPlayersChange,
  maxPlayers = 2,
}: MultiplayerControlsProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [newPlayerName, setNewPlayerName] = useState('')

  const addPlayer = () => {
    if (!newPlayerName.trim() || players.length >= maxPlayers) return
    
    const newPlayer: Player = {
      id: generateId(),
      name: newPlayerName.trim(),
      avatarInitial: newPlayerName.trim()[0].toUpperCase(),
    }
    
    onPlayersChange([...players, newPlayer])
    setNewPlayerName('')
  }

  const removePlayer = (playerId: string) => {
    onPlayersChange(players.filter((p) => p.id !== playerId))
  }

  return (
    <div className="border-t border-border pt-4">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-text-secondary hover:text-text-primary transition-colors"
      >
        <div className="flex items-center gap-2">
          <Users size={16} />
          <span className="text-sm font-medium">Multiplayer</span>
          {players.length > 0 && (
            <span className="text-xs text-gold-primary">({players.length} players)</span>
          )}
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown size={16} />
        </motion.div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pt-4 space-y-3">
              {/* Player chips */}
              {players.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {players.map((player) => (
                    <div
                      key={player.id}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-pill bg-surface-raised border border-border"
                    >
                      <AvatarChip
                        initial={player.avatarInitial}
                        name={player.name}
                        size="sm"
                        showName
                      />
                      <button
                        onClick={() => removePlayer(player.id)}
                        className="p-0.5 rounded text-text-disabled hover:text-error transition-colors"
                        aria-label={\`Remove \${player.name}\`}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add player form */}
              {players.length < maxPlayers && (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newPlayerName}
                    onChange={(e) => setNewPlayerName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addPlayer()}
                    placeholder="Player name"
                    className="flex-1 px-3 py-2 rounded-input bg-surface-raised border border-border text-text-primary placeholder:text-text-disabled text-sm focus-ring"
                  />
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={addPlayer}
                    disabled={!newPlayerName.trim()}
                    leftIcon={<Plus size={14} />}
                  >
                    Add
                  </Button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
`,

  // Debate Components
  'src/components/debate/DebateHeader.tsx': `import { ChevronLeft, Settings } from 'lucide-react'
import { Pill } from '@/components/ui/Pill'

interface DebateHeaderProps {
  topic: string
  currentRound: number
  totalRounds: number
  onBack: () => void
  onSettings?: () => void
}

export function DebateHeader({
  topic,
  currentRound,
  totalRounds,
  onBack,
  onSettings,
}: DebateHeaderProps) {
  return (
    <header className="sticky top-0 z-40 bg-background/85 backdrop-blur-md border-b border-border px-4 py-3">
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors focus-ring"
          aria-label="Go back"
        >
          <ChevronLeft size={20} />
        </button>

        <h1 className="flex-1 text-[15px] font-semibold text-text-primary truncate">
          {topic}
        </h1>

        <Pill size="sm" className="flex-shrink-0">
          R{currentRound}/{totalRounds}
        </Pill>

        {onSettings && (
          <button
            onClick={onSettings}
            className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors focus-ring"
            aria-label="Settings"
          >
            <Settings size={18} />
          </button>
        )}
      </div>
    </header>
  )
}
`,

  'src/components/debate/TimerBar.tsx': `import { motion } from 'framer-motion'
import { clsx } from 'clsx'

interface TimerBarProps {
  timeRemaining: number
  totalTime: number
  currentRound: number
  totalRounds: number
  completedRounds: number[]
}

export function TimerBar({
  timeRemaining,
  totalTime,
  currentRound,
  totalRounds,
  completedRounds,
}: TimerBarProps) {
  const minutes = Math.floor(timeRemaining / 60)
  const seconds = timeRemaining % 60
  const timeString = \`\${minutes}:\${seconds.toString().padStart(2, '0')}\`
  const percentRemaining = (timeRemaining / totalTime) * 100
  const isWarning = timeRemaining <= 15

  // Calculate stroke dasharray for circular timer
  const radius = 24
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference * (1 - percentRemaining / 100)

  return (
    <div className="bg-surface rounded-card p-3 space-y-3">
      <div className="flex items-center gap-4">
        {/* Circular timer */}
        <div className="relative w-14 h-14 flex-shrink-0">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 56 56">
            {/* Background circle */}
            <circle
              cx="28"
              cy="28"
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              className="text-border"
            />
            {/* Progress circle */}
            <motion.circle
              cx="28"
              cy="28"
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
              className={isWarning ? 'text-error' : 'text-gold-primary'}
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: 0 }}
              animate={{ strokeDashoffset }}
              transition={{ duration: 0.5 }}
            />
          </svg>
          {/* Time display */}
          <span
            className={clsx(
              'absolute inset-0 flex items-center justify-center text-sm font-bold',
              isWarning ? 'text-error pulse-warning' : 'text-gold-primary'
            )}
            role="timer"
            aria-label={\`\${minutes} minutes and \${seconds} seconds remaining\`}
          >
            {timeString}
          </span>
        </div>

        {/* Round progress */}
        <div className="flex-1">
          <div className="flex gap-1">
            {Array.from({ length: totalRounds }).map((_, i) => {
              const roundNum = i + 1
              const isCompleted = completedRounds.includes(roundNum)
              const isCurrent = roundNum === currentRound

              return (
                <div
                  key={roundNum}
                  className={clsx(
                    'flex-1 h-1 rounded-full transition-colors duration-300',
                    isCompleted && 'bg-gold-primary',
                    isCurrent && !isCompleted && 'bg-gold-primary/50',
                    !isCompleted && !isCurrent && 'bg-border'
                  )}
                />
              )
            })}
          </div>
          <p className="text-caption text-text-disabled mt-1.5">
            Round {currentRound} of {totalRounds}
          </p>
        </div>
      </div>
    </div>
  )
}
`,

  'src/components/debate/ScoreStrip.tsx': `import { motion, AnimatePresence } from 'framer-motion'
import { AvatarChip } from '@/components/ui/AvatarChip'

interface ScoreStripProps {
  userName: string
  userScore: number
  aiScore: number
  userScoreChange?: number
  aiScoreChange?: number
}

export function ScoreStrip({
  userName,
  userScore,
  aiScore,
  userScoreChange,
  aiScoreChange,
}: ScoreStripProps) {
  return (
    <div className="flex items-center justify-between py-2 px-1">
      <ScoreChip
        name={userName}
        initial={userName[0]?.toUpperCase() || 'U'}
        score={userScore}
        scoreChange={userScoreChange}
        variant="gold"
      />

      <span className="text-text-disabled text-sm font-medium px-3">VS</span>

      <ScoreChip
        name="FlipSide"
        initial="FS"
        score={aiScore}
        scoreChange={aiScoreChange}
        variant="surface"
        isAi
      />
    </div>
  )
}

interface ScoreChipProps {
  name: string
  initial: string
  score: number
  scoreChange?: number
  variant: 'gold' | 'surface'
  isAi?: boolean
}

function ScoreChip({ name, initial, score, scoreChange, variant, isAi }: ScoreChipProps) {
  return (
    <div className="flex items-center gap-2">
      {!isAi && <AvatarChip initial={initial} size="sm" variant={variant} showName={false} />}
      {isAi && <AvatarChip initial={initial} size="sm" variant={variant} showName={false} />}
      
      <div className={isAi ? 'text-right' : ''}>
        <p className="text-xs text-text-secondary">{name}</p>
        <div className="relative">
          <span className="text-lg font-bold text-gold-primary">{score}</span>
          
          <AnimatePresence>
            {scoreChange && scoreChange > 0 && (
              <motion.span
                initial={{ opacity: 1, y: 0 }}
                animate={{ opacity: 0, y: -20 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 1 }}
                className="absolute -right-6 top-0 text-sm text-success font-semibold float-up"
              >
                +{scoreChange}
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
`,

  'src/components/debate/ChatWindow.tsx': `import { useRef, useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import type { Message } from '@/types'
import { MessageRow } from './MessageRow'
import { EmptyState } from '@/components/ui/EmptyState'
import { MessageSquare } from 'lucide-react'

interface ChatWindowProps {
  messages: Message[]
  isAiThinking: boolean
}

export function ChatWindow({ messages, isAiThinking }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isAiThinking])

  if (messages.length === 0 && !isAiThinking) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <EmptyState
          icon={<MessageSquare size={40} />}
          title="Start the debate"
          description="Make your first argument to begin"
        />
      </div>
    )
  }

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
      role="log"
      aria-live="polite"
      aria-label="Debate messages"
    >
      <AnimatePresence initial={false}>
        {messages.map((message) => (
          <MessageRow key={message.id} message={message} />
        ))}
        
        {isAiThinking && (
          <MessageRow
            key="typing"
            message={{
              id: 'typing',
              role: 'ai',
              content: '',
              timestamp: Date.now(),
              roundNumber: 0,
            }}
            isTyping
          />
        )}
      </AnimatePresence>
    </div>
  )
}
`,

  'src/components/debate/MessageRow.tsx': `import { motion } from 'framer-motion'
import type { Message } from '@/types'
import { AvatarChip } from '@/components/ui/AvatarChip'
import { clsx } from 'clsx'

interface MessageRowProps {
  message: Message
  isTyping?: boolean
}

export function MessageRow({ message, isTyping }: MessageRowProps) {
  const isUser = message.role === 'user'
  const timestamp = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, x: isUser ? 10 : -10 }}
      animate={{ opacity: 1, y: 0, x: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className={clsx('flex gap-2', isUser ? 'justify-end' : 'justify-start')}
    >
      {!isUser && (
        <AvatarChip initial="FS" size="sm" variant="gold" showName={false} />
      )}

      <div
        className={clsx(
          'max-w-[75%] rounded-2xl px-4 py-3',
          isUser
            ? 'bg-gold-glow border border-gold-primary/30 rounded-br-sm'
            : 'bg-surface-raised border border-border rounded-bl-sm'
        )}
      >
        {isTyping ? (
          <div className="flex gap-1 py-1">
            <span className="w-2 h-2 rounded-full bg-text-secondary typing-dot" />
            <span className="w-2 h-2 rounded-full bg-text-secondary typing-dot" />
            <span className="w-2 h-2 rounded-full bg-text-secondary typing-dot" />
          </div>
        ) : (
          <>
            <p className="text-sm text-text-primary whitespace-pre-wrap">
              {message.content}
            </p>
            <p className="text-[10px] text-text-disabled mt-1.5 text-right">
              {timestamp}
            </p>
          </>
        )}
      </div>
    </motion.div>
  )
}
`,

  'src/components/debate/CoachPanel.tsx': `import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Brain, ChevronDown, RefreshCw } from 'lucide-react'
import { Skeleton } from '@/components/ui/Skeleton'
import { clsx } from 'clsx'

interface CoachPanelProps {
  tip: string | null
  isLoading: boolean
  onRefresh: () => void
  disabled?: boolean
}

export function CoachPanel({ tip, isLoading, onRefresh, disabled }: CoachPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    if (tip && !isExpanded) {
      setIsExpanded(true)
    }
  }, [tip, isExpanded])

  return (
    <div className="px-4">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        disabled={disabled}
        className={clsx(
          'w-full flex items-center justify-between py-2',
          'text-gold-muted hover:text-gold-primary transition-colors',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <div className="flex items-center gap-2">
          <Brain size={16} />
          <span className="text-sm font-medium">Coach</span>
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown size={16} />
        </motion.div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="glass-surface rounded-card p-3 mb-3">
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton width="90%" height={14} />
                  <Skeleton width="70%" height={14} />
                </div>
              ) : tip ? (
                <div className="flex items-start gap-2">
                  <p className="text-sm text-text-primary flex-1">{tip}</p>
                  <button
                    onClick={onRefresh}
                    className="p-1 rounded text-text-disabled hover:text-gold-primary transition-colors"
                    aria-label="Get new tip"
                  >
                    <RefreshCw size={14} />
                  </button>
                </div>
              ) : (
                <p className="text-sm text-text-secondary">
                  Make an argument to get coaching tips
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
`,

  'src/components/debate/InputRow.tsx': `import { useState, useRef, useEffect, useCallback } from 'react'
import { ArrowUp, Mic } from 'lucide-react'
import { clsx } from 'clsx'

interface InputRowProps {
  onSubmit: (content: string) => void
  disabled?: boolean
  isLoading?: boolean
}

export function InputRow({ onSubmit, disabled, isLoading }: InputRowProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [isRecording, setIsRecording] = useState(false)

  const handleSubmit = useCallback(() => {
    if (!value.trim() || disabled || isLoading) return
    onSubmit(value.trim())
    setValue('')
  }, [value, disabled, isLoading, onSubmit])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
    }
  }, [value])

  return (
    <div className="sticky bottom-0 bg-background/92 backdrop-blur-xl border-t border-border p-3">
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Make your argument..."
            disabled={disabled}
            rows={1}
            className={clsx(
              'w-full px-4 py-3 rounded-input bg-surface-raised border border-border',
              'text-text-primary placeholder:text-text-disabled resize-none',
              'focus-ring transition-colors',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
            style={{ maxHeight: 120 }}
          />
        </div>

        <button
          onClick={() => setIsRecording(!isRecording)}
          className={clsx(
            'w-11 h-11 rounded-input flex items-center justify-center transition-all',
            isRecording
              ? 'bg-gold-primary text-background ring-2 ring-gold-primary ring-offset-2 ring-offset-background'
              : 'bg-surface-raised text-text-secondary hover:text-text-primary'
          )}
          aria-label={isRecording ? 'Stop recording' : 'Start voice input'}
        >
          <Mic size={20} />
        </button>

        <button
          onClick={handleSubmit}
          disabled={!value.trim() || disabled || isLoading}
          className={clsx(
            'w-11 h-11 rounded-input flex items-center justify-center transition-colors',
            value.trim() && !disabled && !isLoading
              ? 'bg-gold-primary text-background hover:bg-gold-primary/90'
              : 'bg-surface-raised text-text-disabled cursor-not-allowed'
          )}
          aria-label="Send message"
        >
          {isLoading ? (
            <span className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
          ) : (
            <ArrowUp size={20} />
          )}
        </button>
      </div>

      <p className="text-[10px] text-text-disabled text-center mt-2">
        Press Cmd+Enter to send
      </p>
    </div>
  )
}
`,

  'src/components/debate/RoundEndOverlay.tsx': `import { motion } from 'framer-motion'
import { Trophy, X, Minus } from 'lucide-react'
import type { Round } from '@/types'
import { Button } from '@/components/ui/Button'
import { clsx } from 'clsx'

interface RoundEndOverlayProps {
  round: Round
  verdict: string
  onContinue: () => void
  isLastRound: boolean
}

export function RoundEndOverlay({
  round,
  verdict,
  onContinue,
  isLastRound,
}: RoundEndOverlayProps) {
  const winnerLabel = 
    round.winner === 'user' ? 'You Won!' :
    round.winner === 'ai' ? 'FlipSide Won' :
    "It's a Tie!"

  const WinnerIcon = 
    round.winner === 'user' ? Trophy :
    round.winner === 'ai' ? X :
    Minus

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Backdrop */}
      <motion.div
        className="absolute inset-0 glass-surface"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      />

      {/* Content */}
      <motion.div
        className="relative z-10 text-center max-w-sm"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        <div
          className={clsx(
            'w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4',
            round.winner === 'user' && 'bg-success/20 text-success',
            round.winner === 'ai' && 'bg-error/20 text-error',
            round.winner === 'tie' && 'bg-gold-glow text-gold-primary'
          )}
        >
          <WinnerIcon size={32} />
        </div>

        <h2 className="text-display text-text-primary mb-2">Round {round.number}</h2>
        
        <p
          className={clsx(
            'text-h1 font-bold mb-4',
            round.winner === 'user' && 'text-success',
            round.winner === 'ai' && 'text-error',
            round.winner === 'tie' && 'text-gold-primary'
          )}
        >
          {winnerLabel}
        </p>

        <p className="text-text-secondary mb-6 px-4">{verdict}</p>

        <div className="flex justify-center gap-4 mb-6 text-sm">
          <span className="text-text-secondary">
            You: <span className="text-gold-primary font-bold">{round.userScore}</span>
          </span>
          <span className="text-text-disabled">|</span>
          <span className="text-text-secondary">
            FlipSide: <span className="text-gold-primary font-bold">{round.aiScore}</span>
          </span>
        </div>

        <Button onClick={onContinue} size="lg" fullWidth>
          {isLastRound ? 'See Results' : 'Next Round →'}
        </Button>
      </motion.div>
    </motion.div>
  )
}
`,

  // Stats Components
  'src/components/stats/VerdictCard.tsx': `import { motion } from 'framer-motion'
import { Trophy, Frown, Scale } from 'lucide-react'
import type { Verdict } from '@/types'
import { clsx } from 'clsx'

interface VerdictCardProps {
  verdict: Verdict
  userScore: number
  aiScore: number
}

export function VerdictCard({ verdict, userScore, aiScore }: VerdictCardProps) {
  const Icon = 
    verdict.winner === 'user' ? Trophy :
    verdict.winner === 'ai' ? Frown :
    Scale

  const winnerLabel = 
    verdict.winner === 'user' ? 'Victory!' :
    verdict.winner === 'ai' ? 'Defeat' :
    'Draw'

  return (
    <motion.div
      className="glass-surface rounded-card p-6 relative overflow-hidden"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Animated border */}
      <motion.div
        className="absolute inset-0 rounded-card"
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(212,168,67,0.3), transparent)',
          backgroundSize: '200% 100%',
        }}
        animate={{
          backgroundPosition: ['100% 0', '-100% 0'],
        }}
        transition={{
          duration: 2,
          ease: 'linear',
          repeat: Infinity,
        }}
      />

      <div className="relative z-10">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Icon
            size={32}
            className={clsx(
              verdict.winner === 'user' && 'text-success',
              verdict.winner === 'ai' && 'text-error',
              verdict.winner === 'tie' && 'text-gold-primary'
            )}
          />
          <h2
            className={clsx(
              'text-display',
              verdict.winner === 'user' && 'text-success',
              verdict.winner === 'ai' && 'text-error',
              verdict.winner === 'tie' && 'text-gold-primary'
            )}
          >
            {winnerLabel}
          </h2>
        </div>

        <p className="text-h3 text-text-primary text-center mb-4">
          You {userScore} — FlipSide {aiScore}
        </p>

        <p className="text-body text-text-secondary text-center">
          {verdict.summary}
        </p>
      </div>
    </motion.div>
  )
}
`,

  'src/components/stats/ScoreBreakdown.tsx': `import { motion } from 'framer-motion'
import { MessageSquare, Trophy, Clock, TrendingUp, TrendingDown, Lightbulb } from 'lucide-react'
import type { Round } from '@/types'
import { getAverageResponseTime, getStrongestRound, getWeakestRound } from '@/lib/scoring'

interface ScoreBreakdownProps {
  rounds: Round[]
  messagesCount: number
  coachTipsUsed: number
}

export function ScoreBreakdown({ rounds, messagesCount, coachTipsUsed }: ScoreBreakdownProps) {
  const userWins = rounds.filter((r) => r.winner === 'user').length
  const avgResponseTime = getAverageResponseTime(rounds)
  const strongestRound = getStrongestRound(rounds)
  const weakestRound = getWeakestRound(rounds)

  const stats = [
    { label: 'Arguments Made', value: messagesCount, icon: MessageSquare },
    { label: 'Rounds Won', value: userWins, icon: Trophy },
    { label: 'Avg Response', value: \`\${avgResponseTime}s\`, icon: Clock },
    { label: 'Strongest Round', value: strongestRound || '-', icon: TrendingUp },
    { label: 'Weakest Round', value: weakestRound || '-', icon: TrendingDown },
    { label: 'Coach Tips', value: coachTipsUsed, icon: Lightbulb },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {stats.map((stat, index) => (
        <motion.div
          key={stat.label}
          className="bg-surface-raised rounded-card p-4 text-center"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 + 0.2 }}
        >
          <stat.icon size={18} className="mx-auto mb-2 text-text-disabled" />
          <p className="text-caption text-text-secondary mb-1">{stat.label}</p>
          <CountingNumber value={stat.value} />
        </motion.div>
      ))}
    </div>
  )
}

interface CountingNumberProps {
  value: string | number
}

function CountingNumber({ value }: CountingNumberProps) {
  // For string values, just display them
  if (typeof value === 'string') {
    return <p className="text-h2 text-gold-primary font-bold">{value}</p>
  }

  return (
    <motion.p
      className="text-h2 text-gold-primary font-bold"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {value}
    </motion.p>
  )
}
`,

  'src/components/stats/RoundTimeline.tsx': `import { motion } from 'framer-motion'
import { Trophy, X, Minus } from 'lucide-react'
import type { Round } from '@/types'
import { clsx } from 'clsx'

interface RoundTimelineProps {
  rounds: Round[]
}

export function RoundTimeline({ rounds }: RoundTimelineProps) {
  return (
    <div className="overflow-x-auto -mx-4 px-4 pb-2">
      <div className="flex gap-3 min-w-max">
        {rounds.map((round, index) => (
          <motion.div
            key={round.number}
            className={clsx(
              'w-20 flex-shrink-0 rounded-card p-3 text-center border',
              round.winner === 'user'
                ? 'bg-success/10 border-success/30'
                : round.winner === 'ai'
                ? 'bg-surface-raised border-border'
                : 'bg-gold-glow/50 border-gold-primary/30'
            )}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 + 0.3 }}
          >
            <p className="text-caption text-text-secondary mb-1">Round {round.number}</p>
            
            <div className="my-2">
              {round.winner === 'user' ? (
                <Trophy size={20} className="mx-auto text-success" />
              ) : round.winner === 'ai' ? (
                <X size={20} className="mx-auto text-error" />
              ) : (
                <Minus size={20} className="mx-auto text-gold-primary" />
              )}
            </div>

            <p className="text-xs text-text-secondary">
              <span className={round.userScore > round.aiScore ? 'text-success' : ''}>
                +{round.userScore}
              </span>
              {' / '}
              <span className={round.aiScore > round.userScore ? 'text-error' : ''}>
                -{round.aiScore}
              </span>
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
`,

  'src/components/stats/PerformanceChart.tsx': `import { motion } from 'framer-motion'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { Round } from '@/types'

interface PerformanceChartProps {
  rounds: Round[]
}

export function PerformanceChart({ rounds }: PerformanceChartProps) {
  // Calculate cumulative scores
  let userCumulative = 0
  let aiCumulative = 0
  
  const data = rounds.map((round) => {
    userCumulative += round.userScore
    aiCumulative += round.aiScore
    
    return {
      round: \`R\${round.number}\`,
      user: userCumulative,
      ai: aiCumulative,
    }
  })

  return (
    <motion.div
      className="bg-surface rounded-card p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.4, duration: 0.8 }}
    >
      <h3 className="text-label text-text-secondary mb-4">Score Progression</h3>
      
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="userGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#D4A843" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#D4A843" stopOpacity={0} />
              </linearGradient>
            </defs>
            
            <XAxis
              dataKey="round"
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#4A3F2F', fontSize: 11 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#4A3F2F', fontSize: 11 }}
            />
            
            <Tooltip content={<CustomTooltip />} />
            
            <Area
              type="monotone"
              dataKey="ai"
              stroke="#9E8E6F"
              strokeWidth={2}
              fill="none"
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="user"
              stroke="#D4A843"
              strokeWidth={2}
              fill="url(#userGradient)"
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex justify-center gap-6 mt-2">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-gold-primary" />
          <span className="text-caption text-text-secondary">You</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-text-secondary" />
          <span className="text-caption text-text-secondary">FlipSide</span>
        </div>
      </div>
    </motion.div>
  )
}

interface TooltipPayload {
  dataKey: string
  value: number
  color: string
}

interface CustomTooltipProps {
  active?: boolean
  payload?: TooltipPayload[]
  label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload) return null

  return (
    <div className="bg-surface-raised border border-gold-primary/30 rounded-lg px-3 py-2">
      <p className="text-caption text-text-secondary mb-1">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="text-sm" style={{ color: entry.color }}>
          {entry.dataKey === 'user' ? 'You' : 'FlipSide'}: {entry.value}
        </p>
      ))}
    </div>
  )
}
`,

  'src/components/stats/ExportControls.tsx': `import { Download, Share2 } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import type { DebateSession } from '@/types'

interface ExportControlsProps {
  session: DebateSession
  onToast: (message: string) => void
}

export function ExportControls({ session, onToast }: ExportControlsProps) {
  const handleExport = () => {
    const transcript = generateTranscript(session)
    const blob = new Blob([transcript], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    
    const a = document.createElement('a')
    a.href = url
    a.download = \`flipside-debate-\${session.id}.txt\`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    onToast('Transcript downloaded!')
  }

  const handleShare = async () => {
    const summary = generateShareSummary(session)
    
    try {
      await navigator.clipboard.writeText(summary)
      onToast('Copied to clipboard!')
    } catch {
      onToast('Failed to copy')
    }
  }

  return (
    <div className="flex gap-3">
      <Button
        variant="outline"
        onClick={handleExport}
        leftIcon={<Download size={16} />}
        className="flex-1"
      >
        Export Transcript
      </Button>
      <Button
        variant="primary"
        onClick={handleShare}
        leftIcon={<Share2 size={16} />}
        className="flex-1"
      >
        Share Result
      </Button>
    </div>
  )
}

function generateTranscript(session: DebateSession): string {
  const lines: string[] = [
    '═══════════════════════════════════════',
    '        FLIPSIDE DEBATE TRANSCRIPT      ',
    '═══════════════════════════════════════',
    '',
    \`Topic: \${session.topic}\`,
    \`Mode: \${session.mode}\`,
    \`Your Side: \${session.side}\`,
    \`Date: \${new Date(session.createdAt).toLocaleDateString()}\`,
    '',
    '───────────────────────────────────────',
    '              TRANSCRIPT               ',
    '───────────────────────────────────────',
    '',
  ]

  session.messages.forEach((msg) => {
    const speaker = msg.role === 'user' ? 'You' : 'FlipSide'
    const time = new Date(msg.timestamp).toLocaleTimeString()
    lines.push(\`[\${time}] \${speaker} (Round \${msg.roundNumber}):\`)
    lines.push(msg.content)
    lines.push('')
  })

  if (session.verdict) {
    lines.push('───────────────────────────────────────')
    lines.push('              VERDICT                  ')
    lines.push('───────────────────────────────────────')
    lines.push('')
    lines.push(\`Winner: \${session.verdict.winner === 'user' ? 'You' : session.verdict.winner === 'ai' ? 'FlipSide' : 'Tie'}\`)
    lines.push(\`Final Score: You \${session.totalUserScore} - FlipSide \${session.totalAiScore}\`)
    lines.push('')
    lines.push(session.verdict.summary)
    lines.push('')
    lines.push('Strengths:')
    session.verdict.strengths.forEach((s) => lines.push(\`  • \${s}\`))
    lines.push('')
    lines.push('Areas for Improvement:')
    session.verdict.weaknesses.forEach((w) => lines.push(\`  • \${w}\`))
  }

  lines.push('')
  lines.push('═══════════════════════════════════════')
  lines.push('        Generated by FlipSide          ')
  lines.push('═══════════════════════════════════════')

  return lines.join('\\n')
}

function generateShareSummary(session: DebateSession): string {
  const winner = session.verdict?.winner
  const result = winner === 'user' ? '🏆 Won' : winner === 'ai' ? '😤 Lost' : '🤝 Tied'
  
  return \`🎯 FlipSide Debate Result

Topic: "\${session.topic}"
Side: \${session.side === 'for' ? 'For' : 'Against'}
Mode: \${session.mode}

Result: \${result}
Score: Me \${session.totalUserScore} - FlipSide \${session.totalAiScore}

\${session.verdict?.summary || ''}

#FlipSide #AIDebate\`
}
`,

  // Screens
  'src/screens/SetupScreen.tsx': `import { useState } from 'react'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'
import type { DebateMode, Side, DebateSession, Player } from '@/types'
import { SetupCard } from '@/components/setup/SetupCard'
import { TopicInput } from '@/components/setup/TopicInput'
import { TopicList } from '@/components/setup/TopicList'
import { ModePills } from '@/components/setup/ModePills'
import { SideSelector } from '@/components/setup/SideSelector'
import { TimerSelect } from '@/components/setup/TimerSelect'
import { MultiplayerControls } from '@/components/setup/MultiplayerControls'
import { HistoryPanel } from '@/components/setup/HistoryPanel'
import { Button } from '@/components/ui/Button'

interface SetupScreenProps {
  onStart: (config: {
    topic: string
    mode: DebateMode
    side: Side
    timerDuration: number
    players: Player[]
  }) => void
  history: DebateSession[]
  onSelectHistory: (session: DebateSession) => void
  onDeleteHistory: (sessionId: string) => void
}

export function SetupScreen({
  onStart,
  history,
  onSelectHistory,
  onDeleteHistory,
}: SetupScreenProps) {
  const [topic, setTopic] = useState('')
  const [mode, setMode] = useState<DebateMode>('balanced')
  const [side, setSide] = useState<Side>('for')
  const [timerDuration, setTimerDuration] = useState(120)
  const [players, setPlayers] = useState<Player[]>([])
  const [error, setError] = useState('')

  const handleStart = () => {
    if (!topic.trim()) {
      setError('Please enter a debate topic')
      return
    }
    setError('')
    onStart({ topic: topic.trim(), mode, side, timerDuration, players })
  }

  const handleTopicSelect = (selectedTopic: string) => {
    setTopic(selectedTopic)
    setError('')
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <motion.div
        className="w-full max-w-md"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-2">
            <Zap size={24} className="text-gold-primary" />
            <h1 className="text-h1 text-gold-primary">FlipSide</h1>
            <span className="px-1.5 py-0.5 rounded bg-surface-raised text-gold-muted text-[10px] font-medium">
              v2
            </span>
          </div>
          <p className="text-body text-text-secondary">
            Your AI Debate Partner
          </p>
        </div>

        {/* Setup Card */}
        <SetupCard>
          <TopicInput
            value={topic}
            onChange={(v) => {
              setTopic(v)
              setError('')
            }}
            error={error}
          />

          <TopicList onSelect={handleTopicSelect} selectedTopic={topic} />

          <ModePills value={mode} onChange={setMode} />

          <SideSelector value={side} onChange={setSide} />

          <TimerSelect value={timerDuration} onChange={setTimerDuration} />

          <MultiplayerControls players={players} onPlayersChange={setPlayers} />

          <Button
            onClick={handleStart}
            fullWidth
            size="lg"
            className="mt-4"
          >
            Start Debate
          </Button>
        </SetupCard>

        {/* History */}
        <HistoryPanel
          sessions={history}
          onSelect={onSelectHistory}
          onDelete={onDeleteHistory}
        />
      </motion.div>
    </div>
  )
}
`,

  'src/screens/DebateScreen.tsx': `import { useState, useCallback, useRef, useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import type { DebateSession, Round } from '@/types'
import { DebateHeader } from '@/components/debate/DebateHeader'
import { TimerBar } from '@/components/debate/TimerBar'
import { ScoreStrip } from '@/components/debate/ScoreStrip'
import { ChatWindow } from '@/components/debate/ChatWindow'
import { CoachPanel } from '@/components/debate/CoachPanel'
import { InputRow } from '@/components/debate/InputRow'
import { RoundEndOverlay } from '@/components/debate/RoundEndOverlay'
import { useTimer } from '@/hooks/useTimer'
import { getCoachTip } from '@/lib/backendClient'

interface DebateScreenProps {
  session: DebateSession
  currentRound: number
  totalRounds: number
  timerDuration: number
  isAiThinking: boolean
  apiKey: string | null
  onSendMessage: (content: string, responseTime: number, timerDuration: number) => Promise<void>
  onEndRound: () => void
  onEndDebate: () => void
  onBack: () => void
}

export function DebateScreen({
  session,
  currentRound,
  totalRounds,
  timerDuration,
  isAiThinking,
  apiKey,
  onSendMessage,
  onEndRound,
  onEndDebate,
  onBack,
}: DebateScreenProps) {
  const [showRoundEnd, setShowRoundEnd] = useState(false)
  const [lastRound, setLastRound] = useState<Round | null>(null)
  const [coachTip, setCoachTip] = useState<string | null>(null)
  const [isLoadingCoach, setIsLoadingCoach] = useState(false)
  const [userScoreChange, setUserScoreChange] = useState<number | undefined>()
  const [aiScoreChange, setAiScoreChange] = useState<number | undefined>()
  const roundStartTime = useRef(Date.now())
  const prevRoundsLength = useRef(session.rounds.length)

  const { timeRemaining, isRunning, start, pause, reset } = useTimer({
    initialTime: timerDuration,
    onComplete: () => {
      // Time's up - end round
      if (currentRound <= totalRounds) {
        handleRoundEnd()
      }
    },
  })

  // Start timer on mount
  useEffect(() => {
    start()
    roundStartTime.current = Date.now()
  }, [start])

  // Watch for round completion
  useEffect(() => {
    if (session.rounds.length > prevRoundsLength.current) {
      const newRound = session.rounds[session.rounds.length - 1]
      setLastRound(newRound)
      setUserScoreChange(newRound.userScore)
      setAiScoreChange(newRound.aiScore)
      setShowRoundEnd(true)
      pause()
      prevRoundsLength.current = session.rounds.length
    }
  }, [session.rounds, pause])

  const handleRoundEnd = useCallback(() => {
    if (session.rounds.length >= totalRounds) {
      onEndDebate()
    } else {
      // Create a placeholder round if timer expired without exchange
      setLastRound({
        number: currentRound,
        winner: 'ai',
        userScore: 0,
        aiScore: 1,
        duration: timerDuration,
      })
      setShowRoundEnd(true)
      pause()
    }
  }, [session.rounds.length, totalRounds, currentRound, timerDuration, pause, onEndDebate])

  const handleContinue = useCallback(() => {
    setShowRoundEnd(false)
    setUserScoreChange(undefined)
    setAiScoreChange(undefined)
    
    if (currentRound >= totalRounds) {
      onEndDebate()
    } else {
      onEndRound()
      reset(timerDuration)
      start()
      roundStartTime.current = Date.now()
    }
  }, [currentRound, totalRounds, onEndDebate, onEndRound, reset, timerDuration, start])

  const handleSendMessage = useCallback(async (content: string) => {
    const responseTime = Math.round((Date.now() - roundStartTime.current) / 1000)
    await onSendMessage(content, responseTime, timerDuration)
  }, [onSendMessage, timerDuration])

  const fetchCoachTip = useCallback(async () => {
    if (!apiKey || session.messages.length < 2) return
    
    const lastUserMsg = [...session.messages].reverse().find((m) => m.role === 'user')
    const lastAiMsg = [...session.messages].reverse().find((m) => m.role === 'ai')
    
    if (!lastUserMsg || !lastAiMsg) return

    setIsLoadingCoach(true)
    try {
      const tip = await getCoachTip(
        apiKey,
        session.topic,
        session.side,
        lastUserMsg.content,
        lastAiMsg.content
      )
      setCoachTip(tip)
    } catch {
      setCoachTip('Focus on providing specific evidence for your claims.')
    } finally {
      setIsLoadingCoach(false)
    }
  }, [apiKey, session.messages, session.topic, session.side])

  // Fetch coach tip after AI responds
  useEffect(() => {
    if (!isAiThinking && session.messages.length >= 2 && apiKey) {
      fetchCoachTip()
    }
  }, [isAiThinking, session.messages.length, apiKey, fetchCoachTip])

  const completedRounds = session.rounds.map((r) => r.number)

  return (
    <div className="h-screen flex flex-col bg-background">
      <DebateHeader
        topic={session.topic}
        currentRound={currentRound}
        totalRounds={totalRounds}
        onBack={onBack}
      />

      <div className="flex-1 flex flex-col overflow-hidden max-w-3xl mx-auto w-full">
        <div className="px-4 py-3 space-y-3">
          <TimerBar
            timeRemaining={timeRemaining}
            totalTime={timerDuration}
            currentRound={currentRound}
            totalRounds={totalRounds}
            completedRounds={completedRounds}
          />

          <ScoreStrip
            userName="You"
            userScore={session.totalUserScore}
            aiScore={session.totalAiScore}
            userScoreChange={userScoreChange}
            aiScoreChange={aiScoreChange}
          />
        </div>

        <ChatWindow messages={session.messages} isAiThinking={isAiThinking} />

        <CoachPanel
          tip={coachTip}
          isLoading={isLoadingCoach}
          onRefresh={fetchCoachTip}
          disabled={!apiKey || session.messages.length < 2}
        />

        <InputRow
          onSubmit={handleSendMessage}
          disabled={isAiThinking || !isRunning}
          isLoading={isAiThinking}
        />
      </div>

      <AnimatePresence>
        {showRoundEnd && lastRound && (
          <RoundEndOverlay
            round={lastRound}
            verdict={
              lastRound.winner === 'user'
                ? 'Strong arguments! You dominated this round.'
                : lastRound.winner === 'ai'
                ? 'FlipSide made compelling points this round.'
                : 'A closely contested round with solid arguments on both sides.'
            }
            onContinue={handleContinue}
            isLastRound={currentRound >= totalRounds}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
`,

  'src/screens/StatsScreen.tsx': `import { motion } from 'framer-motion'
import type { DebateSession } from '@/types'
import { VerdictCard } from '@/components/stats/VerdictCard'
import { ScoreBreakdown } from '@/components/stats/ScoreBreakdown'
import { RoundTimeline } from '@/components/stats/RoundTimeline'
import { PerformanceChart } from '@/components/stats/PerformanceChart'
import { ExportControls } from '@/components/stats/ExportControls'
import { Button } from '@/components/ui/Button'

interface StatsScreenProps {
  session: DebateSession
  onPlayAgain: () => void
  onToast: (message: string) => void
}

export function StatsScreen({ session, onPlayAgain, onToast }: StatsScreenProps) {
  const userMessages = session.messages.filter((m) => m.role === 'user').length

  if (!session.verdict) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-text-secondary">Loading results...</p>
      </div>
    )
  }

  return (
    <motion.div
      className="min-h-screen py-8 px-4"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="max-w-xl mx-auto space-y-6">
        <VerdictCard
          verdict={session.verdict}
          userScore={session.totalUserScore}
          aiScore={session.totalAiScore}
        />

        <ScoreBreakdown
          rounds={session.rounds}
          messagesCount={userMessages}
          coachTipsUsed={0}
        />

        <RoundTimeline rounds={session.rounds} />

        {session.rounds.length > 1 && (
          <PerformanceChart rounds={session.rounds} />
        )}

        <ExportControls session={session} onToast={onToast} />

        <Button onClick={onPlayAgain} fullWidth size="lg">
          Debate Again
        </Button>
      </div>
    </motion.div>
  )
}
`,

  // Main FlipSide component
  'src/FlipSideNew.tsx': `import { useState, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import type { Screen, DebateMode, Side, Player, DebateSession, Round, Verdict } from '@/types'
import { SetupScreen } from '@/screens/SetupScreen'
import { DebateScreen } from '@/screens/DebateScreen'
import { StatsScreen } from '@/screens/StatsScreen'
import { ToastContainer } from '@/components/ui/Toast'
import { useDebate } from '@/hooks/useDebate'
import { useToast } from '@/hooks/useToast'
import { useLocalStorage } from '@/hooks/useLocalStorage'
import { getHistory, deleteSession } from '@/lib/storage'

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -16 },
}

const pageTransition = {
  duration: 0.35,
  ease: [0.22, 1, 0.36, 1],
}

export function FlipSide() {
  const [screen, setScreen] = useState<Screen>('setup')
  const [apiKey] = useLocalStorage<string | null>('flipside_api_key', null)
  const [history, setHistory] = useLocalStorage<DebateSession[]>('flipside_history', [])
  const [timerDuration, setTimerDuration] = useState(120)
  const [totalRounds] = useState(5)
  const { toasts, addToast, removeToast } = useToast()

  const handleRoundEnd = useCallback((round: Round) => {
    console.log('Round ended:', round)
  }, [])

  const handleDebateEnd = useCallback((verdict: Verdict) => {
    console.log('Debate ended:', verdict)
    setScreen('stats')
  }, [])

  const {
    session,
    currentRound,
    isAiThinking,
    startDebate,
    sendMessage,
    endRound,
    endDebate,
    resetDebate,
  } = useDebate({
    apiKey,
    totalRounds,
    onRoundEnd: handleRoundEnd,
    onDebateEnd: handleDebateEnd,
  })

  const handleStart = useCallback((config: {
    topic: string
    mode: DebateMode
    side: Side
    timerDuration: number
    players: Player[]
  }) => {
    setTimerDuration(config.timerDuration)
    startDebate(config.topic, config.mode, config.side, config.timerDuration)
    setScreen('debate')
  }, [startDebate])

  const handleSelectHistory = useCallback((selectedSession: DebateSession) => {
    // For now, just show a toast - could implement review mode
    addToast('info', \`Viewing: \${selectedSession.topic}\`)
  }, [addToast])

  const handleDeleteHistory = useCallback((sessionId: string) => {
    deleteSession(sessionId)
    setHistory(getHistory())
    addToast('success', 'Debate deleted')
  }, [setHistory, addToast])

  const handleBack = useCallback(() => {
    if (window.confirm('Are you sure you want to leave? Your progress will be lost.')) {
      resetDebate()
      setScreen('setup')
    }
  }, [resetDebate])

  const handlePlayAgain = useCallback(() => {
    setHistory(getHistory())
    resetDebate()
    setScreen('setup')
  }, [resetDebate, setHistory])

  return (
    <div className="min-h-screen bg-background">
      <AnimatePresence mode="wait">
        {screen === 'setup' && (
          <motion.div
            key="setup"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
          >
            <SetupScreen
              onStart={handleStart}
              history={history}
              onSelectHistory={handleSelectHistory}
              onDeleteHistory={handleDeleteHistory}
            />
          </motion.div>
        )}

        {screen === 'debate' && session && (
          <motion.div
            key="debate"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
          >
            <DebateScreen
              session={session}
              currentRound={currentRound}
              totalRounds={totalRounds}
              timerDuration={timerDuration}
              isAiThinking={isAiThinking}
              apiKey={apiKey}
              onSendMessage={sendMessage}
              onEndRound={endRound}
              onEndDebate={endDebate}
              onBack={handleBack}
            />
          </motion.div>
        )}

        {screen === 'stats' && session && (
          <motion.div
            key="stats"
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={pageTransition}
          >
            <StatsScreen
              session={session}
              onPlayAgain={handlePlayAgain}
              onToast={(msg) => addToast('success', msg)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
`,

  // App.tsx
  'src/AppNew.tsx': `import { FlipSide } from './FlipSideNew'
import './index.css'

function App() {
  return <FlipSide />
}

export default App
`,
}

async function main() {
  console.log('🚀 FlipSide 2.0 Setup Script\\n')

  // Create directories
  console.log('📁 Creating directories...')
  for (const dir of directories) {
    try {
      await mkdir(join(ROOT, dir), { recursive: true })
      console.log(\`  ✓ \${dir}\`)
    } catch (err) {
      if (err.code !== 'EEXIST') {
        console.error(\`  ✗ Failed to create \${dir}:\`, err.message)
      }
    }
  }

  // Create files
  console.log('\\n📝 Creating files...')
  for (const [filepath, content] of Object.entries(files)) {
    try {
      await writeFile(join(ROOT, filepath), content)
      console.log(\`  ✓ \${filepath}\`)
    } catch (err) {
      console.error(\`  ✗ Failed to create \${filepath}:\`, err.message)
    }
  }

  console.log(\`
✅ Setup complete!

Next steps:
1. Run: npm install
2. Run: npm run dev
3. Open http://localhost:5173

To use the new architecture:
- Update main.tsx to import from AppNew.tsx
- Or rename AppNew.tsx to App.tsx

Happy debating! 🎯
\`)
}

main().catch(console.error)
