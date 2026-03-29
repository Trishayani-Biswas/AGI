import { useState, useCallback, useEffect, useMemo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { GalaxySetupScene } from './components/GalaxySetupScene'
import { useToast } from './lib/useToast'
import { useLocalStorage } from './lib/useLocalStorage'
import { checkBackendHealth, runAriaResearch, type AriaResearchRun } from './lib/backendClient'
import { buildPresetTopics } from './lib/topicLibrary'
import { DecisionGraphScene } from './components/DecisionGraphScene'
import './FlipSide3d.css'

type Screen = 'galaxy' | 'decision'

export default function FlipSide3D() {
  const [screen, setScreen] = useState<Screen>('galaxy')
  const [backendUrl, setBackendUrl] = useLocalStorage<string>(
    'flipside_backend_url',
    (import.meta.env.VITE_BACKEND_URL as string | undefined)?.trim() || 'http://localhost:8787'
  )
  const { toasts, addToast, removeToast } = useToast()
  const [backendHealthy, setBackendHealthy] = useState(false)
  const [isRunningResearch, setIsRunningResearch] = useState(false)
  const [latestResearchRun, setLatestResearchRun] = useState<AriaResearchRun | null>(null)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [settingsBackendUrl, setSettingsBackendUrl] = useState('')
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

  const handleSelectTopic = useCallback((topic: string) => {
    void topic
  }, [])

  const handleStartResearch = useCallback(async (config: { topic: string; depth: 'quick' | 'standard' | 'deep'; maxSources: number }) => {
    if (!hasBackend || !backendHealthy) {
      addToast('error', 'Backend is offline. Start server and try again.')
      return
    }

    setIsRunningResearch(true)
    try {
      const run = await runAriaResearch(backendUrl, {
        topic: config.topic,
        depth: config.depth,
        maxSources: config.maxSources,
      })
      setLatestResearchRun(run)
      setScreen('decision')
      addToast('success', 'ARIA research completed. Decision graph updated.')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Research request failed.'
      addToast('error', message)
    } finally {
      setIsRunningResearch(false)
    }
  }, [hasBackend, backendHealthy, addToast, backendUrl])

  const handleStartDecisionGraph = useCallback(() => {
    setScreen('decision')
  }, [])

  const handleDecisionGraphBack = useCallback(() => {
    setScreen('galaxy')
  }, [])

  const handleOpenSettings = useCallback(() => {
    setSettingsBackendUrl(backendUrl)
    setIsSettingsOpen(true)
  }, [backendUrl])

  const handleSaveSettings = useCallback(() => {
    setBackendUrl(settingsBackendUrl.trim() || 'http://localhost:8787')
    setIsSettingsOpen(false)
    addToast('info', 'Backend URL updated')
  }, [settingsBackendUrl, setBackendUrl, addToast])

  return (
    <div className="fs3d-root">
      <AnimatePresence mode="wait">
        {screen === 'galaxy' && (
          <motion.div
            key="galaxy"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="fs3d-screen"
          >
            <GalaxySetupScene
              onSelectTopic={handleSelectTopic}
              onStartResearch={handleStartResearch}
              onStartDecisionGraph={handleStartDecisionGraph}
              presetTopics={presetTopics}
            />
            {isRunningResearch ? <div className="fs3d-loading-fallback">Running ARIA research...</div> : null}
          </motion.div>
        )}

        {screen === 'decision' && (
          <motion.div
            key="decision"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4 }}
            className="fs3d-screen"
          >
            <DecisionGraphScene onBack={handleDecisionGraphBack} researchRun={latestResearchRun} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toast notifications */}
      <div className="fs3d-toast-stack">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.9 }}
              className={`fs3d-toast fs3d-toast-${toast.type}`}
              onClick={() => removeToast(toast.id)}
            >
              <span className="fs3d-toast-icon">{toast.type === 'success' ? '✅' : toast.type === 'error' ? '❌' : 'ℹ️'}</span>
              {toast.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Settings button (floating) */}
      <button
        onClick={handleOpenSettings}
        className="fs3d-settings-btn"
        title="Settings"
      >
        ⚙️
      </button>

      <AnimatePresence>
        {isSettingsOpen ? (
          <motion.div
            className="fs3d-settings-modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="fs3d-settings-modal"
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.98 }}
            >
              <h2 className="fs3d-settings-title">Connection Settings</h2>
              <label className="fs3d-settings-label" htmlFor="backend-url-input">Backend URL</label>
              <input
                id="backend-url-input"
                className="fs3d-settings-input"
                type="url"
                value={settingsBackendUrl}
                onChange={(event) => setSettingsBackendUrl(event.target.value)}
                placeholder="http://localhost:8787"
              />
              <div className="fs3d-settings-actions">
                <button
                  type="button"
                  className="fs3d-settings-cancel"
                  onClick={() => setIsSettingsOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="fs3d-settings-save"
                  onClick={handleSaveSettings}
                >
                  Save
                </button>
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
