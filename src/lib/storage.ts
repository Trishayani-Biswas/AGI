import type { DebateSession, AppSettings } from './types'

const STORAGE_KEYS = {
  HISTORY: 'flipside_history',
  API_KEY: 'flipside_api_key',
  SETTINGS: 'flipside_settings',
} as const

// History operations
export function getHistory(): DebateSession[] {
  try {
    const data = localStorage.getItem(STORAGE_KEYS.HISTORY)
    if (!data) return []
    return JSON.parse(data) as DebateSession[]
  } catch {
    console.error('Failed to parse debate history')
    return []
  }
}

export function saveSession(session: DebateSession): void {
  try {
    const history = getHistory()
    const existingIndex = history.findIndex((s) => s.id === session.id)
    
    if (existingIndex >= 0) {
      history[existingIndex] = session
    } else {
      history.unshift(session)
    }
    
    // Keep only last 50 sessions
    const trimmed = history.slice(0, 50)
    localStorage.setItem(STORAGE_KEYS.HISTORY, JSON.stringify(trimmed))
  } catch (error) {
    console.error('Failed to save session:', error)
  }
}

export function deleteSession(sessionId: string): void {
  try {
    const history = getHistory()
    const filtered = history.filter((s) => s.id !== sessionId)
    localStorage.setItem(STORAGE_KEYS.HISTORY, JSON.stringify(filtered))
  } catch (error) {
    console.error('Failed to delete session:', error)
  }
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(STORAGE_KEYS.HISTORY)
  } catch (error) {
    console.error('Failed to clear history:', error)
  }
}

// API Key operations
export function getApiKey(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEYS.API_KEY)
  } catch {
    return null
  }
}

export function saveApiKey(key: string): void {
  try {
    localStorage.setItem(STORAGE_KEYS.API_KEY, key)
  } catch (error) {
    console.error('Failed to save API key:', error)
  }
}

export function removeApiKey(): void {
  try {
    localStorage.removeItem(STORAGE_KEYS.API_KEY)
  } catch (error) {
    console.error('Failed to remove API key:', error)
  }
}

// Settings operations
const DEFAULT_SETTINGS: AppSettings = {
  apiKey: '',
  defaultMode: 'balanced',
  defaultTimer: 120,
  coachEnabled: true,
}

export function getSettings(): AppSettings {
  try {
    const data = localStorage.getItem(STORAGE_KEYS.SETTINGS)
    if (!data) return DEFAULT_SETTINGS
    return { ...DEFAULT_SETTINGS, ...JSON.parse(data) }
  } catch {
    return DEFAULT_SETTINGS
  }
}

export function saveSettings(settings: Partial<AppSettings>): void {
  try {
    const current = getSettings()
    const updated = { ...current, ...settings }
    localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(updated))
  } catch (error) {
    console.error('Failed to save settings:', error)
  }
}

// Utility to generate unique IDs
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}
