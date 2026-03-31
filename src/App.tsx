import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useResearch } from './hooks/useResearch'
import { ariaClient } from './services/ariaClient'
import type { AgentOutput, ResearchRun } from './services/types'
import { LiveBackdrop } from './components/LiveBackdrop'
import signalNetworkImage from './assets/signal-network.svg'
import adversarialFlowImage from './assets/adversarial-flow.svg'
import confidenceRingsImage from './assets/confidence-rings.svg'
import './App.css'

const AGENT_META = [
  { key: 'advocate', title: 'Advocate', subtitle: 'Pro Position Evidence', tone: 'advocate' },
  { key: 'skeptic', title: 'Skeptic', subtitle: 'Counterfactual Pressure', tone: 'skeptic' },
  { key: 'domain', title: 'Domain', subtitle: 'Ground-Truth Baseline', tone: 'domain' }
] as const

const HEADLINE_PULSES = ['strategic', 'adversarial', 'decision-grade', 'live']

const STAGE_POINTS = [
  'Evidence lanes stay isolated by design.',
  'Contradictions are surfaced before recommendations.',
  'Confidence stays visible with every claim.'
]

const METHOD_STEPS = [
  {
    title: 'Frame',
    detail: 'Define topic boundaries and a precise decision question.'
  },
  {
    title: 'Contest',
    detail: 'Run Advocate and Skeptic in parallel while Domain anchors fact pattern.'
  },
  {
    title: 'Resolve',
    detail: 'Arbitrator synthesizes outputs, confidence, and unresolved gaps.'
  }
]

function formatPercent(value: number) {
  return `${Math.max(0, Math.min(100, value)).toFixed(0)}%`
}

function AgentCard({
  title,
  subtitle,
  tone,
  data,
  loading
}: {
  title: string
  subtitle: string
  tone: string
  data?: AgentOutput
  loading: boolean
}) {
  const confidence = data?.confidence ? formatPercent(data.confidence * 100) : '--'

  return (
    <article className={`agent-tile ${tone}`}>
      <header>
        <p>{title}</p>
        <span>{subtitle}</span>
      </header>

      <div className="agent-inline-metric">
        <small>Confidence</small>
        <strong>{confidence}</strong>
      </div>

      {loading && <p className="agent-state">Collecting live findings...</p>}
      {!loading && !data && <p className="agent-state">No findings yet. Start a run to populate this lane.</p>}

      {!loading && data && (
        <>
          <ul className="agent-findings">
            {data.findings.slice(0, 4).map((finding) => (
              <li key={finding}>{finding}</li>
            ))}
          </ul>

          <div className="agent-sources">
            <small>Sources</small>
            <ul>
              {data.sources.slice(0, 3).map((source) => (
                <li key={source}>
                  <a href={source} target="_blank" rel="noreferrer">
                    {source}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </article>
  )
}

function App() {
  const pulseIndexRef = useRef(0)
  const [topic, setTopic] = useState('')
  const [query, setQuery] = useState('')
  const [requestId, setRequestId] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [history, setHistory] = useState<ResearchRun[]>([])
  const [historyError, setHistoryError] = useState('')
  const [backendOnline, setBackendOnline] = useState(false)
  const [headlinePulse, setHeadlinePulse] = useState(HEADLINE_PULSES[0])

  const { data, loading, error, progress } = useResearch(requestId, {
    enabled: Boolean(requestId),
    pollInterval: 1500,
    maxAttempts: 120
  })

  useEffect(() => {
    const verifyHealth = async () => {
      try {
        await ariaClient.health({ retries: 0, timeout: 3000 })
        setBackendOnline(true)
      } catch {
        setBackendOnline(false)
      }
    }

    verifyHealth()
  }, [])

  const loadHistory = async () => {
    try {
      setHistoryError('')
      const response = await ariaClient.listResearchRuns(6, 0)
      setHistory(response.runs)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to load history right now.'
      setHistoryError(message)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  useEffect(() => {
    if (data?.status === 'complete' || data?.status === 'error') {
      loadHistory()
    }
  }, [data?.status])

  useEffect(() => {
    const root = document.documentElement

    const handleScroll = () => {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight
      const ratio = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0
      root.style.setProperty('--scroll-progress', `${Math.max(0, Math.min(100, ratio))}%`)
    }

    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      window.removeEventListener('scroll', handleScroll)
    }
  }, [])

  useEffect(() => {
    const sections = document.querySelectorAll<HTMLElement>('.reveal-section')
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.14, rootMargin: '0px 0px -8% 0px' }
    )

    sections.forEach((section) => observer.observe(section))

    return () => {
      observer.disconnect()
    }
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      pulseIndexRef.current = (pulseIndexRef.current + 1) % HEADLINE_PULSES.length
      setHeadlinePulse(HEADLINE_PULSES[pulseIndexRef.current])
    }, 2200)

    return () => {
      window.clearInterval(timer)
    }
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitError('')

    if (!topic.trim() || !query.trim()) {
      setSubmitError('Topic and question are both required to start ARIA research.')
      return
    }

    try {
      setIsSubmitting(true)
      const response = await ariaClient.startResearch({
        topic: topic.trim(),
        query: query.trim()
      })
      setRequestId(response.request_id)
      await loadHistory()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Request failed'
      setSubmitError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const statusText = useMemo(() => {
    if (!requestId) return 'Idle'
    if (data?.status === 'complete') return 'Complete'
    if (data?.status === 'error') return 'Failed'
    if (loading || data?.status === 'queued' || data?.status === 'running') return 'Running'
    return 'Waiting'
  }, [requestId, data, loading])

  const resolvedTopic = data?.topic || topic || 'No topic selected'
  const confidenceScore = data?.results?.arbitrator.confidence_score
  const confidenceText = confidenceScore ? formatPercent(confidenceScore * 100) : '--'
  const activeFindings =
    (data?.results?.advocate.findings.length || 0) +
    (data?.results?.skeptic.findings.length || 0) +
    (data?.results?.domain.findings.length || 0)

  const activityFeed = [
    `Status: ${statusText}`,
    `Request: ${requestId || 'Not started'}`,
    `Confidence: ${confidenceText}`,
    `Findings: ${activeFindings}`
  ]

  return (
    <main className="aria-site">
      <LiveBackdrop />
      <div className="scroll-progress" aria-hidden="true" />

      <aside className="left-rail">
        <p className="rail-mark">ARIA</p>
        <nav>
          <a href="#stage">Stage</a>
          <a href="#control">Control</a>
          <a href="#evidence">Evidence</a>
          <a href="#archive">Archive</a>
        </nav>
      </aside>

      <div className="site-shell">
        <section className="stage reveal-section is-visible" id="stage">
          <article className="manifesto-panel">
            <p className="eyebrow">MULTI-AGENT DECISION FABRIC</p>
            <h1>ARIA is not a chatbot UI. It is a pressure chamber for decisions.</h1>
            <p className="pulse-line">Now running in {headlinePulse} mode</p>
            <p>
              A studio-grade surface where competing arguments are generated, challenged,
              and resolved into one synthesis that carries confidence and traceability.
            </p>

            <ul>
              {STAGE_POINTS.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>

            <div className="status-chip-row">
              <span className={`status-chip ${backendOnline ? 'online' : 'offline'}`}>
                {backendOnline ? 'Backend online' : 'Backend offline'}
              </span>
              <span className="status-chip neutral">{statusText}</span>
            </div>
          </article>

          <article className="monitor-panel">
            <p className="panel-kicker">Live Monitor</p>
            <h2>{resolvedTopic}</h2>
            <p>{requestId || 'No active request'}</p>

            <div className="meter-wrap">
              <progress max={100} value={Math.min(100, Math.max(0, progress))} />
              <span>{formatPercent(progress)}</span>
            </div>

            <div className="monitor-grid">
              <article>
                <small>Signals</small>
                <strong>{activeFindings}</strong>
              </article>
              <article>
                <small>Confidence</small>
                <strong>{confidenceText}</strong>
              </article>
            </div>

            <a href="#control" className="action-link">
              Launch new run
            </a>
          </article>
        </section>

        <section className="visual-band reveal-section">
          <figure>
            <img src={signalNetworkImage} alt="Signal network visualization" />
          </figure>
          <figure>
            <img src={adversarialFlowImage} alt="Adversarial flow diagram" />
          </figure>
          <figure>
            <img src={confidenceRingsImage} alt="Confidence field diagram" />
          </figure>
        </section>

        <section className="method-strip reveal-section">
          {METHOD_STEPS.map((step, index) => (
            <article key={step.title}>
              <p>{`0${index + 1}`}</p>
              <h3>{step.title}</h3>
              <span>{step.detail}</span>
            </article>
          ))}
        </section>

        <section className="command-deck reveal-section" id="control">
          <article className="launch-panel">
            <header>
              <p className="eyebrow">CONTROL SURFACE</p>
              <h2>Start a research run</h2>
            </header>

            <form onSubmit={handleSubmit}>
              <label>
                Topic
                <input
                  value={topic}
                  onChange={(event) => setTopic(event.target.value)}
                  placeholder="Example: Carbon removal policy"
                />
              </label>

              <label>
                Research Query
                <textarea
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  rows={5}
                  placeholder="Define the exact claim or decision that requires adversarial analysis."
                />
              </label>

              <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Starting...' : 'Start ARIA Run'}
              </button>
            </form>

            {submitError && <p className="error-text">{submitError}</p>}
          </article>

          <article className="feed-panel">
            <header>
              <p className="eyebrow">TELEMETRY FEED</p>
              <h2>Session stream</h2>
            </header>

            <ul>
              {activityFeed.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>

            <div className="synthesis-box">
              <h3>Arbitrator synthesis</h3>
              <p>{data?.results?.arbitrator.synthesis || 'Synthesis appears once all agent streams converge.'}</p>
              <div className="synthesis-meta">
                <span>Recommendation</span>
                <strong>{data?.results?.arbitrator.recommendation || '--'}</strong>
              </div>
            </div>

            {error && <p className="error-text">{error.message}</p>}
          </article>
        </section>

        <section className="evidence-stage reveal-section" id="evidence">
          <div className="section-title-row">
            <h2>Evidence lanes</h2>
            <p>Each lane preserves adversarial intent before synthesis.</p>
          </div>

          <div className="agents-grid">
            {AGENT_META.map((agent) => (
              <AgentCard
                key={agent.key}
                title={agent.title}
                subtitle={agent.subtitle}
                tone={agent.tone}
                loading={loading || data?.status === 'queued' || data?.status === 'running'}
                data={data?.results?.[agent.key]}
              />
            ))}
          </div>
        </section>

        <section className="archive-stage reveal-section" id="archive">
          <article className="archive-header">
            <h2>Run archive</h2>
            <button type="button" onClick={loadHistory}>
              Refresh
            </button>
          </article>

          {historyError && <p className="error-text">{historyError}</p>}

          <div className="history-grid">
            {history.length === 0 && <p className="history-empty">No runs yet.</p>}
            {history.map((run) => (
              <article key={run.request_id} className="history-card">
                <p>{run.topic}</p>
                <span className={`history-status ${run.status}`}>{run.status}</span>
                <small>{run.request_id}</small>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}

export default App
