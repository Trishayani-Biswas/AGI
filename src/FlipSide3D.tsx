import { useState, useCallback, useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useToast } from './lib/useToast'
import { useLocalStorage } from './lib/useLocalStorage'
import { checkBackendHealth, runAriaResearch, type AriaResearchRun } from './lib/backendClient'
import { CoreOctantScene } from './components/CoreOctantScene'
import './FlipSide3d.css'

type ResearchDepth = 'quick' | 'standard' | 'deep'

export default function FlipSide3D() {
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
  const [showCoreSection, setShowCoreSection] = useState(false)
  const [tvShutdown, setTvShutdown] = useState(false)

  const [topic, setTopic] = useState('')
  const [wordLength, setWordLength] = useState(900)
  const [tone, setTone] = useState('Balanced')
  const [outputType, setOutputType] = useState('Report')
  const [depth, setDepth] = useState<ResearchDepth>('standard')
  const [maxSources, setMaxSources] = useState(6)

  const inputSectionRef = useRef<HTMLElement | null>(null)
  const coreSectionRef = useRef<HTMLElement | null>(null)

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

  const handleStartResearch = useCallback(async () => {
    if (!topic.trim()) {
      addToast('error', 'Topic is required before starting ARIA research.')
      return
    }

    if (!hasBackend || !backendHealthy) {
      addToast('error', 'Backend is offline. Start server and try again.')
      return
    }

    setTvShutdown(true)
    setShowCoreSection(true)
    setIsRunningResearch(true)

    window.setTimeout(() => {
      coreSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 620)

    try {
      const run = await runAriaResearch(backendUrl, {
        topic: topic.trim(),
        depth,
        maxSources,
      })
      setLatestResearchRun(run)
      addToast('success', 'ARIA research completed. Core node map updated.')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Research request failed.'
      addToast('error', message)
    } finally {
      window.setTimeout(() => setTvShutdown(false), 1200)
      setIsRunningResearch(false)
    }
  }, [topic, hasBackend, backendHealthy, addToast, backendUrl, depth, maxSources])

  const handleOpenSettings = useCallback(() => {
    setSettingsBackendUrl(backendUrl)
    setIsSettingsOpen(true)
  }, [backendUrl])

  const handleSaveSettings = useCallback(() => {
    setBackendUrl(settingsBackendUrl.trim() || 'http://localhost:8787')
    setIsSettingsOpen(false)
    addToast('info', 'Backend URL updated')
  }, [settingsBackendUrl, setBackendUrl, addToast])

  const handleGetStarted = useCallback(() => {
    inputSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const resultTopic = latestResearchRun?.topic || 'Pending Research Topic'
  const outputSummary = latestResearchRun
    ? latestResearchRun.agents.arbitrator.summary
    : 'Primary output will appear here after ARIA completes the first run.'
  const guideSummary = latestResearchRun
    ? latestResearchRun.agents.domain.summary
    : 'Guide agent will track standards, context, and domain constraints.'
  const decisionLog = latestResearchRun
    ? `${latestResearchRun.claims.length} claims | ${latestResearchRun.contradictions.length} contradictions | ${latestResearchRun.evidence.length} evidence sources`
    : 'Decision and change log will activate after your first run.'

  return (
    <div className="fs3d-root fs3d-site-root">
      <div className={`fs3d-tv-shutdown ${tvShutdown ? 'is-active' : ''}`} aria-hidden="true" />

      <main className="fs3d-scroll-site">
        <section className="fs3d-landing-section">
          <div className="fs3d-landing-content">
            <p className="fs3d-overline">FlipSide ARIA Demo</p>
            <h1 className="fs3d-landing-title">Node Based Research Theater</h1>
            <p className="fs3d-landing-copy">
              Open the experience, let the drums roll, and enter your challenge. ARIA agents then occupy the top octants while
              outputs and decisions anchor the lower field.
            </p>
            <button type="button" className="fs3d-cta-btn" onClick={handleGetStarted}>
              Let the drums roll
            </button>
          </div>
        </section>

        <section ref={inputSectionRef} className="fs3d-input-section">
          <div className="fs3d-input-shell">
            <h2 className="fs3d-section-title">Input Panel</h2>
            <p className="fs3d-section-copy">Enter your request and launch Start Research with ARIA.</p>

            <label className="fs3d-input-label" htmlFor="topic-input">Topic</label>
            <textarea
              id="topic-input"
              className="fs3d-input-textarea"
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="Type your research prompt here..."
              rows={4}
            />

            <div className="fs3d-input-grid">
              <div>
                <label className="fs3d-input-label" htmlFor="word-length">Word Length</label>
                <input
                  id="word-length"
                  className="fs3d-input-control"
                  type="number"
                  min={200}
                  max={3000}
                  value={wordLength}
                  onChange={(event) => setWordLength(Number(event.target.value) || 900)}
                />
              </div>

              <div>
                <label className="fs3d-input-label" htmlFor="tone">Tone</label>
                <select id="tone" className="fs3d-input-control" value={tone} onChange={(event) => setTone(event.target.value)}>
                  <option>Balanced</option>
                  <option>Academic</option>
                  <option>Concise</option>
                </select>
              </div>

              <div>
                <label className="fs3d-input-label" htmlFor="output-type">Output Type</label>
                <select
                  id="output-type"
                  className="fs3d-input-control"
                  value={outputType}
                  onChange={(event) => setOutputType(event.target.value)}
                >
                  <option>Report</option>
                  <option>Brief</option>
                  <option>Lesson Plan</option>
                </select>
              </div>

              <div>
                <label className="fs3d-input-label" htmlFor="depth">Research Depth</label>
                <select
                  id="depth"
                  className="fs3d-input-control"
                  value={depth}
                  onChange={(event) => setDepth(event.target.value as ResearchDepth)}
                >
                  <option value="quick">Quick</option>
                  <option value="standard">Standard</option>
                  <option value="deep">Deep</option>
                </select>
              </div>

              <div>
                <label className="fs3d-input-label" htmlFor="source-breadth">Source Breadth</label>
                <select
                  id="source-breadth"
                  className="fs3d-input-control"
                  value={maxSources}
                  onChange={(event) => setMaxSources(Number(event.target.value))}
                >
                  <option value={4}>4 sources</option>
                  <option value={6}>6 sources</option>
                  <option value={8}>8 sources</option>
                </select>
              </div>
            </div>

            <div className="fs3d-input-meta">
              <span>{backendHealthy ? 'Backend online' : 'Backend offline'}</span>
              <span>{wordLength} words</span>
              <span>{tone}</span>
              <span>{outputType}</span>
            </div>

            <button type="button" className="fs3d-research-btn" onClick={handleStartResearch} disabled={isRunningResearch}>
              {isRunningResearch ? 'Running ARIA...' : 'Start Research with ARIA'}
            </button>
          </div>
        </section>

        <section
          ref={coreSectionRef}
          className={`fs3d-core-section ${showCoreSection ? 'is-visible' : ''}`}
          aria-live="polite"
        >
          <div className="fs3d-core-canvas">
            <CoreOctantScene
              researchRun={latestResearchRun}
              outputSummary={outputSummary}
              guideSummary={guideSummary}
              decisionLog={decisionLog}
            />
          </div>
        </section>
      </main>

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
