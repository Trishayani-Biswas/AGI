import { useState, useCallback, useEffect, useMemo, lazy, Suspense } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { GalaxySetupScene } from './components/GalaxySetupScene'
import type { DebateMode, Side, DebateSession, Verdict } from './lib/types'
import { useDebate } from './lib/useDebate'
import { useToast } from './lib/useToast'
import { useTimer } from './lib/useTimer'
import { useLocalStorage } from './lib/useLocalStorage'
import { getHistory } from './lib/storage'
import { checkBackendHealth } from './lib/backendClient'
import { buildPresetTopics } from './lib/topicLibrary'

type Screen = 'galaxy' | 'solar' | 'cosmos'

const SolarDebateScene = lazy(async () => {
  const module = await import('./components/SolarDebateScene')
  return { default: module.SolarDebateScene }
})

const CosmicStatsScene = lazy(async () => {
  const module = await import('./components/CosmicStatsScene')
  return { default: module.CosmicStatsScene }
})

function SceneLoadingFallback() {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#020208',
        color: 'rgba(220, 230, 255, 0.8)',
        fontSize: 14,
        letterSpacing: '0.06em',
      }}
    >
      Loading scene...
    </div>
  )
}

export default function FlipSide3D() {
  const [screen, setScreen] = useState<Screen>('galaxy')
  const [apiKey, setApiKey] = useLocalStorage<string | null>('flipside_api_key', null)
  const [backendUrl] = useLocalStorage<string>(
    'flipside_backend_url',
    (import.meta.env.VITE_BACKEND_URL as string | undefined)?.trim() || 'http://localhost:8787'
  )
  const [, setHistory] = useLocalStorage<DebateSession[]>('flipside_history', [])
  const [timerDuration, setTimerDuration] = useState(120)
  const [totalRounds] = useState(5)
  const { toasts, addToast, removeToast } = useToast()
  const [backendHealthy, setBackendHealthy] = useState(false)
  const presetTopics = useMemo(() => buildPresetTopics(1200), [])

  // Check backend health
  const hasBackend = backendUrl.trim().length > 0
  useEffect(() => {
    let cancelled = false
    const run = async () => {
      if (!hasBackend) {
        setBackendHealthy(false)
        return
      }
      try {
        await checkBackendHealth(backendUrl)
        if (!cancelled) setBackendHealthy(true)
      } catch {
        if (!cancelled) setBackendHealthy(false)
      }
    }
    void run()
    return () => { cancelled = true }
  }, [backendUrl, hasBackend])

  const handleDebateEnd = useCallback((verdict: Verdict) => {
    void verdict
    setScreen('cosmos')
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
    backendUrl: hasBackend && backendHealthy ? backendUrl : null,
    totalRounds,
    onDebateEnd: handleDebateEnd,
  })

  // Timer for debate screen
  const { timeRemaining, start, pause, reset } = useTimer({
    initialTime: timerDuration,
    onComplete: () => {
      if (!isAiThinking && currentRound <= totalRounds) {
        if (currentRound >= totalRounds) {
          endDebate()
        } else {
          endRound()
          reset(timerDuration)
          start()
        }
      }
    },
  })

  // Watch for round completion to advance timer
  useEffect(() => {
    if (session && session.rounds.length > 0) {
      const lastRound = session.rounds[session.rounds.length - 1]
      if (lastRound && lastRound.number === currentRound - 1) {
        // Round just completed, timer should already be reset
      }
      if (session.rounds.length >= totalRounds) {
        pause()
        endDebate()
      }
    }
  }, [session, currentRound, totalRounds, endDebate, pause])

  const handleSelectTopic = useCallback((topic: string) => {
    void topic
  }, [])

  const handleStartDebate = useCallback((config: { topic: string; mode: DebateMode; side: Side; timerDuration: number }) => {
    setTimerDuration(config.timerDuration)
    startDebate(config.topic, config.mode, config.side, config.timerDuration)
    reset(config.timerDuration)
    start()
    setScreen('solar')
  }, [startDebate, reset, start])

  const handleBack = useCallback(() => {
    if (window.confirm('Leave debate? Progress will be lost.')) {
      pause()
      resetDebate()
      setScreen('galaxy')
    }
  }, [pause, resetDebate])

  const handlePlayAgain = useCallback(() => {
    setHistory(getHistory())
    resetDebate()
    setScreen('galaxy')
  }, [resetDebate, setHistory])

  const handleExport = useCallback(() => {
    if (!session) return
    const lines = [
      '═══════════════════════════════════════',
      '        FLIPSIDE DEBATE TRANSCRIPT      ',
      '═══════════════════════════════════════',
      '',
      `Topic: ${session.topic}`,
      `Mode: ${session.mode}`,
      `Date: ${new Date(session.createdAt).toLocaleDateString()}`,
      '',
      ...session.messages.map((m) => `[${m.role === 'user' ? 'You' : 'FlipSide'}]: ${m.content}`),
      '',
      `Final Score: You ${session.totalUserScore} - FlipSide ${session.totalAiScore}`,
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `flipside-debate-${session.id}.txt`
    a.click()
    URL.revokeObjectURL(url)
    addToast('success', 'Transcript downloaded!')
  }, [session, addToast])

  const handleShare = useCallback(async () => {
    if (!session) return
    const summary = `🎯 FlipSide Debate\nTopic: "${session.topic}"\nScore: Me ${session.totalUserScore} - FlipSide ${session.totalAiScore}`
    try {
      await navigator.clipboard.writeText(summary)
      addToast('success', 'Copied to clipboard!')
    } catch {
      addToast('error', 'Clipboard unavailable')
    }
  }, [session, addToast])

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: '#000' }}>
      <AnimatePresence mode="wait">
        {screen === 'galaxy' && (
          <motion.div
            key="galaxy"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            style={{ width: '100%', height: '100%' }}
          >
            <GalaxySetupScene
              onSelectTopic={handleSelectTopic}
              onStartDebate={handleStartDebate}
              presetTopics={presetTopics}
            />
          </motion.div>
        )}

        {screen === 'solar' && session && (
          <motion.div
            key="solar"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.1 }}
            transition={{ duration: 0.6 }}
            style={{ width: '100%', height: '100%' }}
          >
            <Suspense fallback={<SceneLoadingFallback />}>
              <SolarDebateScene
                session={session}
                currentRound={currentRound}
                totalRounds={totalRounds}
                isAiThinking={isAiThinking}
                timeRemaining={timeRemaining}
                timerDuration={timerDuration}
                onSendMessage={sendMessage}
                onBack={handleBack}
              />
            </Suspense>
          </motion.div>
        )}

        {screen === 'cosmos' && session && (
          <motion.div
            key="cosmos"
            initial={{ opacity: 0, scale: 1.2 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
            style={{ width: '100%', height: '100%' }}
          >
            <Suspense fallback={<SceneLoadingFallback />}>
              <CosmicStatsScene
                session={session}
                onPlayAgain={handlePlayAgain}
                onExport={handleExport}
                onShare={handleShare}
              />
            </Suspense>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toast notifications */}
      <div
        style={{
          position: 'fixed',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 100,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.9 }}
              style={{
                background: 'rgba(10, 10, 20, 0.95)',
                backdropFilter: 'blur(10px)',
                borderRadius: 16,
                padding: '12px 20px',
                border: `1px solid ${
                  toast.type === 'success' ? '#30d158' : toast.type === 'error' ? '#ff453a' : '#8b5cf6'
                }`,
                color: '#fff',
                fontSize: 14,
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                cursor: 'pointer',
              }}
              onClick={() => removeToast(toast.id)}
            >
              {toast.type === 'success' ? '✅' : toast.type === 'error' ? '❌' : 'ℹ️'}
              {toast.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Settings button (floating) */}
      <button
        onClick={() => {
          const newKey = window.prompt('Enter Anthropic API Key (leave empty to clear):', apiKey || '')
          if (newKey !== null) {
            setApiKey(newKey.trim() || null)
            addToast('success', newKey.trim() ? 'API key saved' : 'API key cleared')
          }
        }}
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 48,
          height: 48,
          borderRadius: '50%',
          background: 'rgba(139, 92, 246, 0.2)',
          border: '1px solid rgba(139, 92, 246, 0.4)',
          color: '#8b5cf6',
          cursor: 'pointer',
          fontSize: 20,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
        }}
        title="Settings"
      >
        ⚙️
      </button>
    </div>
  )
}
