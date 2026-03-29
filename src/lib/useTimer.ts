import { useState, useEffect, useCallback, useRef } from 'react'

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
