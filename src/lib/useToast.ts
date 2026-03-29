import { useState, useCallback } from 'react'
import type { ToastMessage } from './types'
import { generateId } from './storage'

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
