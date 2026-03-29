import { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, ArrowUp, ChevronLeft, Clock, Trash2, ChevronDown, ThumbsUp, ThumbsDown, Trophy, X as XIcon, Minus } from 'lucide-react'
import type { DebateMode, Side, DebateSession, Verdict, ToastMessage, Player } from './lib/types'
import { useDebate } from './lib/useDebate'
import { useToast } from './lib/useToast'
import { useTimer } from './lib/useTimer'
import { useLocalStorage } from './lib/useLocalStorage'
import { getHistory, deleteSession } from './lib/storage'
import { checkBackendHealth, getCoachTip, getNewsTopicSuggestions, type NewsTopicSuggestion } from './lib/backendClient'

type Screen = 'setup' | 'debate' | 'stats'

const pageTransition = {
  duration: 0.35,
  ease: [0.22, 1, 0.36, 1] as const,
}

// Inline styles using CSS variables
const colors = {
  background: '#F4F7FB',
  surface: '#FFFFFF',
  surfaceRaised: '#F8FAFC',
  border: '#DCE3ED',
  goldPrimary: '#0A84FF',
  goldMuted: '#5CA8FF',
  goldGlow: 'rgba(10, 132, 255, 0.12)',
  textPrimary: '#0B172A',
  textSecondary: '#475467',
  textDisabled: '#98A2B3',
  error: '#FF5D73',
  success: '#30D0A3',
}

// ============ UI COMPONENTS ============

function Button({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled = false,
  isLoading = false,
  leftIcon,
  onClick,
  style,
}: {
  children: React.ReactNode
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  fullWidth?: boolean
  disabled?: boolean
  isLoading?: boolean
  leftIcon?: React.ReactNode
  onClick?: () => void
  style?: React.CSSProperties
}) {
  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    fontWeight: 600,
    borderRadius: '10px',
    cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
    opacity: disabled || isLoading ? 0.5 : 1,
    transition: 'all 0.2s',
    border: 'none',
    outline: 'none',
    ...(size === 'sm' && { height: '32px', padding: '0 12px', fontSize: '12px' }),
    ...(size === 'md' && { height: '40px', padding: '0 16px', fontSize: '14px' }),
    ...(size === 'lg' && { height: '48px', padding: '0 24px', fontSize: '16px' }),
    ...(fullWidth && { width: '100%' }),
    ...(variant === 'primary' && {
      background: 'linear-gradient(135deg, #0A84FF, #5CA8FF)',
      color: '#FFFFFF',
      boxShadow: '0 12px 28px rgba(10,132,255,0.28)',
    }),
    ...(variant === 'secondary' && { background: colors.surfaceRaised, color: colors.textPrimary, border: `1px solid ${colors.border}` }),
    ...(variant === 'outline' && { background: 'transparent', color: colors.goldPrimary, border: `1px solid ${colors.goldPrimary}` }),
    ...style,
  }

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled || isLoading}
      style={baseStyle}
      whileTap={{ scale: disabled || isLoading ? 1 : 0.97 }}
      whileHover={{ opacity: disabled ? 0.5 : 0.96, y: disabled ? 0 : -1 }}
    >
      {isLoading ? (
        <span style={{ width: 16, height: 16, border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      ) : (
        <>
          {leftIcon}
          {children}
        </>
      )}
    </motion.button>
  )
}

function Pill({
  children,
  isSelected = false,
  onClick,
  size = 'md',
}: {
  children: React.ReactNode
  isSelected?: boolean
  onClick?: () => void
  size?: 'sm' | 'md'
}) {
  const style: React.CSSProperties = {
    padding: size === 'sm' ? '4px 10px' : '8px 16px',
    fontSize: size === 'sm' ? '12px' : '14px',
    fontWeight: 500,
    borderRadius: '9999px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    border: `1px solid ${isSelected ? colors.goldPrimary : colors.border}`,
    background: isSelected ? colors.goldPrimary : colors.surfaceRaised,
    color: isSelected ? colors.background : colors.textSecondary,
  }

  return (
    <motion.button onClick={onClick} style={style} whileTap={{ scale: 0.97 }}>
      {children}
    </motion.button>
  )
}

function AvatarChip({ initial, size = 'md' }: { initial: string; size?: 'sm' | 'md' }) {
  const dim = size === 'sm' ? 24 : 32
  return (
    <span style={{
      width: dim, height: dim, borderRadius: '50%',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: colors.goldPrimary, color: colors.background,
      fontSize: size === 'sm' ? '10px' : '12px', fontWeight: 600, textTransform: 'uppercase',
    }}>
      {initial}
    </span>
  )
}

function ToastContainer({ toasts, onRemove }: { toasts: ToastMessage[]; onRemove: (id: string) => void }) {
  return (
    <div style={{ position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)', zIndex: 50, display: 'flex', flexDirection: 'column', gap: 8 }}>
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            style={{
              background: 'rgba(255, 255, 255, 0.92)',
              backdropFilter: 'blur(12px)',
              borderRadius: 16, padding: '12px 16px',
              border: `1px solid ${toast.type === 'success' ? colors.success : toast.type === 'error' ? colors.error : colors.goldPrimary}`,
              display: 'flex', alignItems: 'center', gap: 12, minWidth: 280,
            }}
          >
            <p style={{ flex: 1, margin: 0, fontSize: 14, color: colors.textPrimary }}>{toast.message}</p>
            <button onClick={() => onRemove(toast.id)} style={{ background: 'none', border: 'none', color: colors.textSecondary, cursor: 'pointer', padding: 4 }}>
              <XIcon size={16} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// ============ SETUP SCREEN ============

function SetupScreen({
  onStart,
  history,
  onDeleteHistory,
  apiKey,
  onApiKeyChange,
  backendUrl,
  onBackendUrlChange,
  newsApiKey,
  onNewsApiKeyChange,
  connectionMode,
}: {
  onStart: (config: { topic: string; mode: DebateMode; side: Side; timerDuration: number; players: Player[] }) => void
  history: DebateSession[]
  onDeleteHistory: (id: string) => void
  apiKey: string | null
  onApiKeyChange: (value: string | null) => void
  backendUrl: string
  onBackendUrlChange: (value: string) => void
  newsApiKey: string | null
  onNewsApiKeyChange: (value: string | null) => void
  connectionMode: 'backend' | 'direct' | 'fallback'
}) {
  const [topic, setTopic] = useState('')
  const [mode, setMode] = useState<DebateMode>('balanced')
  const [side, setSide] = useState<Side>('for')
  const [timerDuration, setTimerDuration] = useState(120)
  const [error, setError] = useState('')
  const [newsError, setNewsError] = useState('')
  const [isLoadingNews, setIsLoadingNews] = useState(false)
  const [newsSuggestions, setNewsSuggestions] = useState<NewsTopicSuggestion[]>([])
  const [historyExpanded, setHistoryExpanded] = useState(false)

  const PRESET_TOPICS = ['AI in Governance', 'UBI vs Meritocracy', 'Space > Earth Problems?', 'Social Media is Toxic']
  const MODES: { value: DebateMode; label: string }[] = [
    { value: 'casual', label: 'Casual' },
    { value: 'balanced', label: 'Balanced' },
    { value: 'intense', label: 'Intense' },
  ]
  const TIMERS = [
    { value: 180, label: '3 min' },
    { value: 120, label: '2 min' },
    { value: 90, label: '90 sec' },
  ]

  const handleStart = () => {
    if (!topic.trim()) {
      setError('Please enter a debate topic')
      return
    }
    onStart({ topic: topic.trim(), mode, side, timerDuration, players: [] })
  }

  const modeLabel = connectionMode === 'backend'
    ? 'Backend + Anthropic (primary)'
    : connectionMode === 'direct'
      ? 'Direct Anthropic API key'
      : 'Fallback mode'

  const handleLoadNewsTopics = async () => {
    const targetUrl = backendUrl.trim() || ((import.meta.env.VITE_BACKEND_URL as string | undefined)?.trim() ?? '')
    if (!targetUrl) {
      setNewsError('Set a backend URL to fetch topic suggestions.')
      return
    }
    setNewsError('')
    setIsLoadingNews(true)
    try {
      const suggestions = await getNewsTopicSuggestions(targetUrl, topic || 'latest policy', 4)
      setNewsSuggestions(suggestions)
      if (suggestions.length === 0) {
        setNewsError('No topic suggestions returned.')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load topic suggestions.'
      setNewsError(message)
      setNewsSuggestions([])
    } finally {
      setIsLoadingNews(false)
    }
  }

  const cardStyle: React.CSSProperties = {
    background: 'linear-gradient(160deg, rgba(255,255,255,0.96), rgba(246,249,253,0.96))',
    backdropFilter: 'blur(10px)',
    borderRadius: 24,
    border: `1px solid ${colors.border}`,
    padding: 24,
    boxShadow: '0 28px 60px rgba(2, 5, 10, 0.65), inset 0 1px 0 rgba(255,255,255,0.03)',
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: 24 }}>
      <motion.div
        style={{
          width: '100%',
          maxWidth: 1080,
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: 20,
          alignItems: 'start',
        }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={pageTransition}
      >
        <div
          style={{
            minHeight: 560,
            borderRadius: 28,
            border: `1px solid ${colors.border}`,
            background: 'linear-gradient(150deg, rgba(255,255,255,0.98), rgba(247,250,253,0.97))',
            boxShadow: '0 24px 56px rgba(15, 23, 42, 0.12), inset 0 1px 0 rgba(255,255,255,0.55)',
            padding: 28,
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div
            aria-hidden="true"
            style={{
              position: 'absolute',
              width: 280,
              height: 280,
              borderRadius: '50%',
              background: 'radial-gradient(circle at center, rgba(10,132,255,0.28), transparent 65%)',
              top: -120,
              right: -80,
            }}
          />
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Zap size={22} style={{ color: colors.goldPrimary }} />
              <span style={{ fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', color: colors.textSecondary }}>Premium Debate Studio</span>
            </div>
            <h2 style={{ margin: '0 0 10px', color: colors.textPrimary, fontSize: 34, lineHeight: 1.08, letterSpacing: '-0.03em' }}>
              Build arguments like a strategist, not a chatbot.
            </h2>
            <p style={{ margin: 0, color: colors.textSecondary, maxWidth: 520, lineHeight: 1.6 }}>
              FlipSide gives you high-pressure rebuttal rounds, adaptive AI difficulty, coaching hints, and clean post-match analytics.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 22 }}>
              {['Adaptive Opponent', 'Round Scoring', 'Coach Insights', 'Export + Share'].map((label) => (
                <div key={label} style={{ border: `1px solid ${colors.border}`, borderRadius: 12, background: colors.surfaceRaised, padding: '10px 12px', color: colors.textPrimary, fontSize: 13 }}>
                  {label}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 26, borderRadius: 16, border: `1px solid ${colors.border}`, background: colors.surface, padding: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ color: colors.textSecondary, fontSize: 12 }}>Session Preview</span>
                <span style={{ color: colors.goldPrimary, fontSize: 12, fontWeight: 700 }}>Live</span>
              </div>
              <div style={{ height: 9, borderRadius: 9999, background: '#E9EFF6', overflow: 'hidden', marginBottom: 10 }}>
                <div style={{ width: '74%', height: '100%', background: 'linear-gradient(90deg,#0A84FF,#5CA8FF)' }} />
              </div>
              <p style={{ margin: 0, fontSize: 12, color: colors.textSecondary }}>
                “Counterpoint quality increased by 28% in intense mode.”
              </p>
            </div>
          </div>
        </div>

        <div>
          <div style={{ textAlign: 'left', marginBottom: 18, paddingLeft: 4 }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Zap size={24} style={{ color: colors.goldPrimary }} />
              <h1 style={{ margin: 0, fontSize: 28, fontWeight: 800, color: colors.textPrimary, letterSpacing: '-0.02em' }}>FlipSide</h1>
              <span style={{ padding: '2px 8px', borderRadius: 9999, background: colors.goldGlow, color: colors.goldPrimary, fontSize: 10, fontWeight: 700 }}>v2</span>
            </div>
             <p style={{ margin: 0, fontSize: 14, color: colors.textSecondary }}>Configure your match and launch.</p>
           </div>

          <motion.div
            style={cardStyle}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, ...pageTransition }}
          >
          {/* Topic Input */}
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: colors.textSecondary, marginBottom: 6 }}>
              Debate Topic
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                value={topic}
                onChange={(e) => { setTopic(e.target.value.slice(0, 200)); setError('') }}
                placeholder="e.g. AI will replace creative jobs"
                style={{
                  width: '100%',
                  padding: '12px 60px 12px 16px',
                  borderRadius: 10,
                  background: colors.surfaceRaised,
                  border: `1px solid ${error ? colors.error : colors.border}`,
                  color: colors.textPrimary,
                  fontSize: 14,
                  outline: 'none',
                  boxSizing: 'border-box',
                  boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)',
                }}
              />
              <span style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', fontSize: 12, color: topic.length > 160 ? colors.error : colors.textDisabled }}>
                {topic.length}/200
              </span>
            </div>
            {error && <p style={{ margin: '6px 0 0', fontSize: 12, color: colors.error }}>{error}</p>}
          </div>

          {/* Preset Topics */}
          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 8, marginBottom: 20 }}>
            {PRESET_TOPICS.map((t) => (
              <button
                key={t}
                onClick={() => { setTopic(t); setError('') }}
                style={{
                  flexShrink: 0,
                  padding: '6px 12px',
                  borderRadius: 9999,
                  fontSize: 12,
                  fontWeight: 500,
                  border: `1px solid ${topic === t ? colors.goldPrimary : colors.border}`,
                  background: topic === t ? colors.goldGlow : colors.surfaceRaised,
                  color: topic === t ? colors.goldPrimary : colors.textSecondary,
                  cursor: 'pointer',
                }}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Mode Pills */}
          <div style={{ marginBottom: 20 }}>
            <span style={{ display: 'block', fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.08em', color: colors.textSecondary, marginBottom: 6 }}>
              Difficulty
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              {MODES.map((m) => (
                <Pill key={m.value} isSelected={mode === m.value} onClick={() => setMode(m.value)}>{m.label}</Pill>
              ))}
            </div>
          </div>

          {/* Side Selector */}
          <div style={{ marginBottom: 20 }}>
            <span style={{ display: 'block', fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.08em', color: colors.textSecondary, marginBottom: 6 }}>
              Your Side
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {(['for', 'against'] as const).map((s) => (
                <motion.button
                  key={s}
                  onClick={() => setSide(s)}
                  style={{
                    height: 80,
                    borderRadius: 16,
                    border: `1px solid ${side === s ? colors.goldPrimary : colors.border}`,
                    background: side === s ? colors.goldGlow : colors.surfaceRaised,
                    color: side === s ? colors.goldPrimary : colors.textSecondary,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    cursor: 'pointer',
                  }}
                  whileTap={{ scale: 0.98 }}
                >
                  {s === 'for' ? <ThumbsUp size={24} /> : <ThumbsDown size={24} />}
                  <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{s}</span>
                </motion.button>
              ))}
            </div>
          </div>

          {/* Timer Select */}
          <div style={{ marginBottom: 24 }}>
            <span style={{ display: 'block', fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.08em', color: colors.textSecondary, marginBottom: 6 }}>
              Round Timer
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              {TIMERS.map((t) => (
                <Pill key={t.value} isSelected={timerDuration === t.value} onClick={() => setTimerDuration(t.value)}>{t.label}</Pill>
              ))}
            </div>
          </div>

            <Button onClick={handleStart} fullWidth size="lg" style={{ borderRadius: 14, fontWeight: 700, letterSpacing: '0.01em' }}>
              Start Debate
            </Button>

            <div style={{ marginTop: 16, borderRadius: 14, border: `1px solid ${colors.border}`, background: colors.surface, padding: 12 }}>
              <p style={{ margin: '0 0 8px', fontSize: 12, color: colors.textSecondary, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                API Setup & Mode
              </p>
              <p style={{ margin: '0 0 10px', fontSize: 13, color: colors.textPrimary, fontWeight: 600 }}>{modeLabel}</p>
              <input
                value={backendUrl}
                onChange={(e) => onBackendUrlChange(e.target.value)}
                placeholder="Backend URL (e.g. http://localhost:8787)"
                style={{
                  width: '100%',
                  marginBottom: 8,
                  padding: '10px 12px',
                  borderRadius: 10,
                  border: `1px solid ${colors.border}`,
                  background: colors.surfaceRaised,
                  color: colors.textPrimary,
                }}
              />
              <input
                value={apiKey ?? ''}
                onChange={(e) => onApiKeyChange(e.target.value.trim() ? e.target.value.trim() : null)}
                placeholder="Anthropic API key (optional for direct mode)"
                style={{
                  width: '100%',
                  marginBottom: 8,
                  padding: '10px 12px',
                  borderRadius: 10,
                  border: `1px solid ${colors.border}`,
                  background: colors.surfaceRaised,
                  color: colors.textPrimary,
                }}
              />
              <input
                value={newsApiKey ?? ''}
                onChange={(e) => onNewsApiKeyChange(e.target.value.trim() ? e.target.value.trim() : null)}
                placeholder="NewsAPI key (optional, backend uses NEWS_API_KEY)"
                style={{
                  width: '100%',
                  marginBottom: 8,
                  padding: '10px 12px',
                  borderRadius: 10,
                  border: `1px solid ${colors.border}`,
                  background: colors.surfaceRaised,
                  color: colors.textPrimary,
                }}
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <Button variant="secondary" size="sm" onClick={handleLoadNewsTopics} isLoading={isLoadingNews}>
                  Suggest Topics
                </Button>
              </div>
              {!!newsError && <p style={{ margin: '8px 0 0', fontSize: 12, color: colors.error }}>{newsError}</p>}
              {newsSuggestions.length > 0 && (
                <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {newsSuggestions.map((item) => (
                    <button
                      key={`${item.source}-${item.title}`}
                      onClick={() => { setTopic(item.title.slice(0, 200)); setError('') }}
                      style={{
                        borderRadius: 9999,
                        border: `1px solid ${colors.border}`,
                        background: colors.surfaceRaised,
                        color: colors.textSecondary,
                        padding: '6px 10px',
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                    >
                      {item.title}
                    </button>
                  ))}
                </div>
              )}
              <p style={{ margin: '10px 0 0', fontSize: 12, color: colors.textSecondary, lineHeight: 1.5 }}>
                Anthropic keys: <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noreferrer" style={{ color: colors.goldPrimary }}>console.anthropic.com/settings/keys</a><br />
                NewsAPI keys: <a href="https://newsapi.org/register" target="_blank" rel="noreferrer" style={{ color: colors.goldPrimary }}>newsapi.org/register</a>
              </p>
            </div>
          </motion.div>

          {/* History Panel */}
          <div style={{ marginTop: 16 }}>
            <button
              onClick={() => setHistoryExpanded(!historyExpanded)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 12,
                borderRadius: 16,
                background: colors.surfaceRaised,
                border: `1px solid ${colors.border}`,
                cursor: 'pointer',
                color: colors.textSecondary,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Clock size={16} />
                <span style={{ fontSize: 14, fontWeight: 500 }}>Past Debates</span>
                {history.length > 0 && (
                  <span style={{ padding: '2px 6px', borderRadius: 9999, background: colors.goldGlow, color: colors.goldPrimary, fontSize: 12, fontWeight: 500 }}>
                    {history.length}
                  </span>
                )}
              </div>
              <motion.div animate={{ rotate: historyExpanded ? 180 : 0 }}>
                <ChevronDown size={16} style={{ color: colors.textDisabled }} />
              </motion.div>
            </button>

            <AnimatePresence>
              {historyExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  style={{ overflow: 'hidden' }}
                >
                  <div style={{ paddingTop: 8, maxHeight: 256, overflowY: 'auto' }}>
                    {history.length === 0 ? (
                      <div style={{ padding: 32, textAlign: 'center', color: colors.textDisabled }}>No debates yet</div>
                    ) : (
                      history.map((s) => (
                        <div
                          key={s.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 12,
                            padding: 12,
                            borderRadius: 16,
                            background: colors.surface,
                            border: `1px solid ${colors.border}`,
                            marginBottom: 8,
                          }}
                        >
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <p style={{ margin: 0, fontSize: 14, color: colors.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.topic}</p>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                              <span style={{ padding: '2px 6px', borderRadius: 4, fontSize: 10, background: colors.surfaceRaised, color: colors.textSecondary, textTransform: 'capitalize' }}>{s.mode}</span>
                              <span style={{ fontSize: 12, color: colors.textDisabled }}>{new Date(s.createdAt).toLocaleDateString()}</span>
                            </div>
                          </div>
                          {s.verdict && (
                            <span style={{
                              fontSize: 12, fontWeight: 600, padding: '4px 8px', borderRadius: 4,
                              background: s.verdict.winner === 'user' ? 'rgba(39, 174, 96, 0.2)' : s.verdict.winner === 'ai' ? 'rgba(192, 57, 43, 0.2)' : colors.goldGlow,
                              color: s.verdict.winner === 'user' ? colors.success : s.verdict.winner === 'ai' ? colors.error : colors.goldPrimary,
                            }}>
                              {s.verdict.winner === 'user' ? 'Won' : s.verdict.winner === 'ai' ? 'Lost' : 'Tie'}
                            </span>
                          )}
                          <button
                            onClick={() => onDeleteHistory(s.id)}
                            style={{ padding: 6, background: 'none', border: 'none', color: colors.textDisabled, cursor: 'pointer' }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

// ============ DEBATE SCREEN ============

function DebateScreen({
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
}: {
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
}) {
  const [coachTip, setCoachTip] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [inputValue, setInputValue] = useState('')
  const roundStartTimeRef = useRef(Date.now())
  const prevRoundsLengthRef = useRef(session.rounds.length)
  const isTransitioningRef = useRef(false)
  const isSendingRef = useRef(false)
  const lastTransitionRoundRef = useRef<number>(0)
  const MAX_INPUT_CHARS = 1200

  const { timeRemaining, isRunning, start, pause, reset } = useTimer({
    initialTime: timerDuration,
    onComplete: () => {
      if (isAiThinking) return
      if (!isTransitioningRef.current && currentRound <= totalRounds) {
        void handleTimeUp()
      }
    },
  })

  // Start timer on mount
  useEffect(() => {
    start()
  }, [start])

  // Watch for round completion
  useEffect(() => {
    if (session.rounds.length > prevRoundsLengthRef.current) {
      const completedRound = session.rounds[session.rounds.length - 1]?.number ?? 0
      if (completedRound > 0 && completedRound === lastTransitionRoundRef.current) {
        prevRoundsLengthRef.current = session.rounds.length
        return
      }
      if (isTransitioningRef.current) return
      isTransitioningRef.current = true
      if (completedRound > 0) {
        lastTransitionRoundRef.current = completedRound
      }
      if (session.rounds.length >= totalRounds || currentRound >= totalRounds) {
        pause()
        onEndDebate()
      } else {
        pause()
        onEndRound()
        reset(timerDuration)
        roundStartTimeRef.current = Date.now()
        start()
      }
      queueMicrotask(() => {
        isTransitioningRef.current = false
      })
    }
    prevRoundsLengthRef.current = session.rounds.length
  }, [session.rounds, currentRound, totalRounds, onEndDebate, onEndRound, pause, reset, start, timerDuration])

  const handleTimeUp = async () => {
    if (isAiThinking) return
    if (isTransitioningRef.current) return
    if (lastTransitionRoundRef.current === currentRound) return
    isTransitioningRef.current = true
    lastTransitionRoundRef.current = currentRound
    if (currentRound >= totalRounds) {
      pause()
      onEndDebate()
    } else {
      pause()
      onEndRound()
      reset(timerDuration)
      roundStartTimeRef.current = Date.now()
      start()
    }
    queueMicrotask(() => {
      isTransitioningRef.current = false
    })
  }

  const handleSubmit = async () => {
    const content = inputValue.trim()
    if (!content) {
      setSubmitError('Message cannot be empty.')
      return
    }
    if (content.length > MAX_INPUT_CHARS) {
      setSubmitError(`Message too long. Max ${MAX_INPUT_CHARS} characters.`)
      return
    }
    if (isAiThinking || !isRunning || isTransitioningRef.current || isSendingRef.current) return
    setSubmitError(null)
    isSendingRef.current = true
    const responseTime = Math.round((Date.now() - roundStartTimeRef.current) / 1000)
    setInputValue('')
    let sentSuccessfully = false
    try {
      await onSendMessage(content, responseTime, timerDuration)
      roundStartTimeRef.current = Date.now()
      sentSuccessfully = true
    } catch {
      setSubmitError('Message failed to send. Please try again.')
      setInputValue(content)
    } finally {
      isSendingRef.current = false
    }

    if (sentSuccessfully && apiKey && session.messages.length >= 1) {
      const lastAiMsg = session.messages.filter(m => m.role === 'ai').pop()?.content || ''
      if (lastAiMsg) {
        try {
          const tip = await getCoachTip(apiKey, session.topic, session.side, content, lastAiMsg)
          setCoachTip(tip)
        } catch {
          setCoachTip(null)
        }
      }
    }
  }

  const minutes = Math.floor(timeRemaining / 60)
  const seconds = timeRemaining % 60
  const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`
  const isWarning = timeRemaining <= 15
  const userMessagesCount = session.messages.filter((m) => m.role === 'user').length

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: colors.background }}>
      {/* Header */}
      <header style={{ position: 'sticky', top: 0, zIndex: 40, background: 'rgba(244, 247, 251, 0.84)', backdropFilter: 'blur(10px)', borderBottom: `1px solid ${colors.border}`, padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onBack} style={{ padding: 6, borderRadius: 8, background: 'none', border: 'none', color: colors.textSecondary, cursor: 'pointer' }}>
            <ChevronLeft size={20} />
          </button>
          <h1 style={{ flex: 1, margin: 0, fontSize: 15, fontWeight: 600, color: colors.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{session.topic}</h1>
          <Pill size="sm">R{currentRound}/{totalRounds}</Pill>
        </div>
      </header>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', maxWidth: 860, margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', gap: 8, padding: '10px 16px 0' }}>
          {[
            { label: 'Mode', value: session.mode.toUpperCase() },
            { label: 'Side', value: session.side.toUpperCase() },
            { label: 'Msgs', value: String(userMessagesCount) },
          ].map((chip) => (
            <div
              key={chip.label}
              style={{
                borderRadius: 9999,
                border: `1px solid ${colors.border}`,
                background: colors.surfaceRaised,
                padding: '6px 10px',
                fontSize: 11,
                color: colors.textSecondary,
                display: 'inline-flex',
                gap: 6,
                alignItems: 'center',
              }}
            >
              <span style={{ color: colors.textDisabled }}>{chip.label}</span>
              <span style={{ color: colors.textPrimary, fontWeight: 700 }}>{chip.value}</span>
            </div>
          ))}
        </div>

        {/* Timer & Score */}
        <div style={{ padding: '12px 16px' }}>
          <div style={{ background: colors.surface, borderRadius: 18, padding: 14, display: 'flex', alignItems: 'center', gap: 16, border: `1px solid ${colors.border}` }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: isWarning ? colors.error : colors.goldPrimary, animation: isWarning ? 'pulse 0.5s infinite' : 'none' }}>
              {timeString}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', gap: 4 }}>
                {Array.from({ length: totalRounds }).map((_, i) => (
                  <div
                    key={i}
                    style={{
                      flex: 1, height: 4, borderRadius: 2,
                      background: session.rounds.some(r => r.number === i + 1) ? colors.goldPrimary :
                        i + 1 === currentRound ? 'rgba(10,132,255,0.35)' : colors.border,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Score */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AvatarChip initial="U" size="sm" />
              <div>
                <p style={{ margin: 0, fontSize: 12, color: colors.textSecondary }}>You</p>
                <span style={{ fontSize: 18, fontWeight: 700, color: colors.goldPrimary }}>{session.totalUserScore}</span>
              </div>
            </div>
            <span style={{ color: colors.textDisabled, fontSize: 14 }}>VS</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ textAlign: 'right' }}>
                <p style={{ margin: 0, fontSize: 12, color: colors.textSecondary }}>FlipSide</p>
                <span style={{ fontSize: 18, fontWeight: 700, color: colors.goldPrimary }}>{session.totalAiScore}</span>
              </div>
              <AvatarChip initial="FS" size="sm" />
            </div>
          </div>
        </div>

        {/* Chat */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {session.messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10, x: msg.role === 'user' ? 10 : -10 }}
              animate={{ opacity: 1, y: 0, x: 0 }}
              style={{ display: 'flex', gap: 8, marginBottom: 16, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
            >
              {msg.role === 'ai' && <AvatarChip initial="FS" size="sm" />}
              <div style={{
                maxWidth: '75%',
                borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                padding: '12px 16px',
                background: msg.role === 'user' ? 'rgba(10,132,255,0.13)' : colors.surfaceRaised,
                border: `1px solid ${msg.role === 'user' ? 'rgba(10,132,255,0.32)' : colors.border}`,
              }}>
                <p style={{ margin: 0, fontSize: 14, color: colors.textPrimary, whiteSpace: 'pre-wrap' }}>{msg.content}</p>
              </div>
            </motion.div>
          ))}
          
          {isAiThinking && (
            <div style={{ display: 'flex', gap: 8 }}>
              <AvatarChip initial="FS" size="sm" />
              <div style={{ background: colors.surfaceRaised, border: `1px solid ${colors.border}`, borderRadius: '16px 16px 16px 4px', padding: '12px 16px' }}>
                <div style={{ display: 'flex', gap: 4 }}>
                  {[0, 1, 2].map((i) => (
                    <span key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: colors.textSecondary, animation: `bounce 1.4s infinite ${i * 0.2}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Coach Tip */}
        {coachTip && (
          <div style={{ padding: '0 16px 8px' }}>
            <div style={{ background: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(12px)', borderRadius: 16, padding: 12, fontSize: 14, color: colors.textPrimary, border: `1px solid ${colors.border}` }}>
              <span style={{ color: colors.goldMuted, fontWeight: 500 }}>💡 Coach: </span>{coachTip}
            </div>
          </div>
        )}

        {/* Input */}
        <div style={{ position: 'sticky', bottom: 0, background: 'rgba(244, 247, 251, 0.94)', backdropFilter: 'blur(12px)', borderTop: `1px solid ${colors.border}`, padding: 12 }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
            <textarea
              value={inputValue}
              onChange={(e) => { setInputValue(e.target.value.slice(0, MAX_INPUT_CHARS)); if (submitError) setSubmitError(null) }}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit() }}
              placeholder="Make your argument..."
              disabled={isAiThinking || !isRunning || isTransitioningRef.current}
              rows={1}
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: 14,
                background: colors.surfaceRaised,
                border: `1px solid ${colors.border}`,
                color: colors.textPrimary,
                fontSize: 14,
                resize: 'none',
                outline: 'none',
                maxHeight: 120,
                fontFamily: 'inherit',
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)',
              }}
            />
            <button
              onClick={handleSubmit}
              disabled={!inputValue.trim() || isAiThinking || !isRunning || isTransitioningRef.current}
              style={{
                width: 46, height: 46, borderRadius: 14,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: inputValue.trim() && !isAiThinking && isRunning ? 'linear-gradient(135deg, #0A84FF, #5CA8FF)' : colors.surfaceRaised,
                color: inputValue.trim() && !isAiThinking && isRunning ? colors.background : colors.textDisabled,
                border: 'none', cursor: inputValue.trim() && !isAiThinking && isRunning ? 'pointer' : 'not-allowed',
              }}
            >
              {isAiThinking ? (
                <span style={{ width: 20, height: 20, border: '2px solid currentColor', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              ) : (
                <ArrowUp size={20} />
              )}
            </button>
          </div>
          {submitError && <p style={{ margin: '8px 0 0', fontSize: 12, color: colors.error, textAlign: 'left' }}>{submitError}</p>}
          <p style={{ margin: '6px 0 0', fontSize: 10, color: inputValue.length > MAX_INPUT_CHARS - 120 ? colors.error : colors.textDisabled, textAlign: 'right' }}>
            {inputValue.length}/{MAX_INPUT_CHARS}
          </p>
          <p style={{ margin: '8px 0 0', fontSize: 10, color: colors.textDisabled, textAlign: 'center' }}>Press Cmd+Enter to send</p>
        </div>
      </div>

      {/* Round transition is automatic to prevent blocking full-screen overlays */}
    </div>
  )
}

// ============ STATS SCREEN ============

function StatsScreen({
  session,
  onPlayAgain,
  onToast,
}: {
  session: DebateSession
  onPlayAgain: () => void
  onToast: (msg: string) => void
}) {
  if (!session.verdict) return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><p style={{ color: colors.textSecondary }}>Loading...</p></div>

  const userMessages = session.messages.filter(m => m.role === 'user').length
  const userWins = session.rounds.filter(r => r.winner === 'user').length
  const totalPoints = Math.max(1, session.totalUserScore + session.totalAiScore)
  const userWinRatio = Math.round((session.totalUserScore / totalPoints) * 100)

  const handleExport = () => {
    const lines = [
      '═══════════════════════════════════════',
      '        FLIPSIDE DEBATE TRANSCRIPT      ',
      '═══════════════════════════════════════',
      '', `Topic: ${session.topic}`, `Mode: ${session.mode}`, `Date: ${new Date(session.createdAt).toLocaleDateString()}`, '',
      ...session.messages.map(m => `[${m.role === 'user' ? 'You' : 'FlipSide'}]: ${m.content}`), '',
      `Final Score: You ${session.totalUserScore} - FlipSide ${session.totalAiScore}`,
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `flipside-debate-${session.id}.txt`
    a.click()
    URL.revokeObjectURL(url)
    onToast('Transcript downloaded!')
  }

  const handleShare = async () => {
    const summary = `🎯 FlipSide Debate\nTopic: "${session.topic}"\nScore: Me ${session.totalUserScore} - FlipSide ${session.totalAiScore}`
    await navigator.clipboard.writeText(summary)
    onToast('Copied to clipboard!')
  }

  return (
    <motion.div
      style={{ minHeight: '100vh', padding: '32px 16px' }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={pageTransition}
    >
      <div style={{ maxWidth: 560, margin: '0 auto' }}>
        {/* Verdict */}
        <motion.div
          style={{ background: 'linear-gradient(160deg, rgba(255,255,255,0.96), rgba(246,249,253,0.96))', backdropFilter: 'blur(12px)', borderRadius: 20, padding: 24, textAlign: 'center', marginBottom: 24, border: `1px solid ${colors.border}` }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div style={{
            width: 64, height: 64, borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
            background: session.verdict.winner === 'user' ? 'rgba(39, 174, 96, 0.2)' : session.verdict.winner === 'ai' ? 'rgba(192, 57, 43, 0.2)' : colors.goldGlow,
            color: session.verdict.winner === 'user' ? colors.success : session.verdict.winner === 'ai' ? colors.error : colors.goldPrimary,
          }}>
            {session.verdict.winner === 'user' ? <Trophy size={32} /> : session.verdict.winner === 'ai' ? <XIcon size={32} /> : <Minus size={32} />}
          </div>
          <h2 style={{
            margin: 0, fontSize: 32, fontWeight: 700,
            color: session.verdict.winner === 'user' ? colors.success : session.verdict.winner === 'ai' ? colors.error : colors.goldPrimary,
          }}>
            {session.verdict.winner === 'user' ? 'Victory!' : session.verdict.winner === 'ai' ? 'Defeat' : 'Draw'}
          </h2>
          <p style={{ margin: '8px 0 0', fontSize: 16, fontWeight: 600, color: colors.textPrimary }}>You {session.totalUserScore} — FlipSide {session.totalAiScore}</p>
          <p style={{ margin: '16px 0 0', fontSize: 14, color: colors.textSecondary }}>{session.verdict.summary}</p>
        </motion.div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Arguments', value: userMessages },
            { label: 'Rounds Won', value: userWins },
            { label: 'Mode', value: session.mode },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              style={{ background: colors.surfaceRaised, borderRadius: 16, padding: 16, textAlign: 'center', border: `1px solid ${colors.border}` }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 + 0.2 }}
            >
              <p style={{ margin: 0, fontSize: 12, color: colors.textSecondary }}>{stat.label}</p>
              <p style={{ margin: '4px 0 0', fontSize: 20, fontWeight: 700, color: colors.goldPrimary, textTransform: 'capitalize' }}>{stat.value}</p>
            </motion.div>
          ))}
        </div>

        <div style={{ marginBottom: 20, borderRadius: 16, border: `1px solid ${colors.border}`, background: colors.surfaceRaised, padding: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: colors.textSecondary }}>Performance Edge</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: colors.goldPrimary }}>{userWinRatio}%</span>
          </div>
          <div style={{ height: 8, borderRadius: 9999, background: '#E9EFF6', overflow: 'hidden' }}>
            <div style={{ width: `${userWinRatio}%`, height: '100%', background: 'linear-gradient(90deg, #0A84FF, #5CA8FF)' }} />
          </div>
        </div>

        {/* Round Timeline */}
        <div style={{ overflowX: 'auto', paddingBottom: 8, marginBottom: 24 }}>
          <div style={{ display: 'flex', gap: 12, minWidth: 'max-content' }}>
            {session.rounds.map((round, i) => (
              <motion.div
                key={round.number}
                style={{
                  width: 80, flexShrink: 0, borderRadius: 16, padding: 12, textAlign: 'center',
                  background: round.winner === 'user' ? 'rgba(48, 208, 163, 0.12)' : round.winner === 'ai' ? colors.surfaceRaised : 'rgba(10,132,255,0.1)',
                  border: `1px solid ${round.winner === 'user' ? 'rgba(48,208,163,0.28)' : round.winner === 'ai' ? colors.border : 'rgba(10,132,255,0.28)'}`,
                }}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 + 0.3 }}
              >
                <p style={{ margin: 0, fontSize: 12, color: colors.textSecondary }}>R{round.number}</p>
                <div style={{ margin: '8px 0' }}>
                  {round.winner === 'user' ? <Trophy size={20} style={{ color: colors.success }} /> :
                   round.winner === 'ai' ? <XIcon size={20} style={{ color: colors.error }} /> :
                   <Minus size={20} style={{ color: colors.goldPrimary }} />}
                </div>
                <p style={{ margin: 0, fontSize: 12, color: colors.textSecondary }}>+{round.userScore} / -{round.aiScore}</p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Export */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <Button variant="outline" onClick={handleExport} style={{ flex: 1 }}>Export</Button>
          <Button variant="primary" onClick={handleShare} style={{ flex: 1 }}>Share</Button>
        </div>

        <Button onClick={onPlayAgain} fullWidth size="lg">Debate Again</Button>
      </div>
    </motion.div>
  )
}

// ============ MAIN APP ============

export default function FlipSide2() {
  const [screen, setScreen] = useState<Screen>('setup')
  const [apiKey, setApiKey] = useLocalStorage<string | null>('flipside_api_key', null)
  const [newsApiKey, setNewsApiKey] = useLocalStorage<string | null>('flipside_news_api_key', null)
  const [backendUrl, setBackendUrl] = useLocalStorage<string>(
    'flipside_backend_url',
    (import.meta.env.VITE_BACKEND_URL as string | undefined)?.trim() || 'http://localhost:8787'
  )
  const [history, setHistory] = useLocalStorage<DebateSession[]>('flipside_history', [])
  const [timerDuration, setTimerDuration] = useState(120)
  const [totalRounds] = useState(5)
  const { toasts, addToast, removeToast } = useToast()
  const [backendHealthy, setBackendHealthy] = useState(false)

  useEffect(() => {
    if (!newsApiKey) return
    const normalized = newsApiKey.trim()
    if (normalized !== newsApiKey) {
      setNewsApiKey(normalized || null)
    }
  }, [newsApiKey, setNewsApiKey])

  const hasBackend = backendUrl.trim().length > 0
  const connectionMode: 'backend' | 'direct' | 'fallback' = hasBackend && backendHealthy
    ? 'backend'
    : apiKey
      ? 'direct'
      : 'fallback'

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
    return () => {
      cancelled = true
    }
  }, [backendUrl, hasBackend])

  const handleDebateEnd = useCallback((verdict: Verdict) => {
    void verdict
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
    backendUrl: hasBackend && backendHealthy ? backendUrl : null,
    totalRounds,
    onDebateEnd: handleDebateEnd,
  })

  const handleStart = useCallback((config: { topic: string; mode: DebateMode; side: Side; timerDuration: number; players: Player[] }) => {
    setTimerDuration(config.timerDuration)
    startDebate(config.topic, config.mode, config.side, config.timerDuration)
    setScreen('debate')
  }, [startDebate])

  const handleDeleteHistory = useCallback((id: string) => {
    deleteSession(id)
    setHistory(getHistory())
    addToast('success', 'Debate deleted')
  }, [setHistory, addToast])

  const handleBack = useCallback(() => {
    if (window.confirm('Leave debate? Progress will be lost.')) {
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
    <div style={{ minHeight: '100vh', background: colors.background, position: 'relative', overflow: 'hidden' }}>
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(900px 500px at 12% -10%, rgba(10,132,255,0.25), transparent 60%), radial-gradient(900px 600px at 100% 0%, rgba(48,208,163,0.14), transparent 55%)',
          pointerEvents: 'none',
        }}
      />
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-4px); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        * { box-sizing: border-box; }
        input::placeholder, textarea::placeholder { color: var(--color-text-disabled); }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-thumb { background: #243347; border-radius: 999px; }
        ::-webkit-scrollbar-track { background: transparent; }
      `}</style>
      
      <div style={{ position: 'relative', zIndex: 1 }}>
      <AnimatePresence mode="wait">
        {screen === 'setup' && (
          <motion.div key="setup" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} transition={pageTransition}>
            <SetupScreen
              onStart={handleStart}
              history={history}
              onDeleteHistory={handleDeleteHistory}
              apiKey={apiKey}
              onApiKeyChange={setApiKey}
              backendUrl={backendUrl}
              onBackendUrlChange={setBackendUrl}
              newsApiKey={newsApiKey}
              onNewsApiKeyChange={setNewsApiKey}
              connectionMode={connectionMode}
            />
          </motion.div>
        )}

        {screen === 'debate' && session && (
          <motion.div key="debate" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} transition={pageTransition}>
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
          <motion.div key="stats" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -16 }} transition={pageTransition}>
            <StatsScreen session={session} onPlayAgain={handlePlayAgain} onToast={(msg) => addToast('success', msg)} />
          </motion.div>
        )}
      </AnimatePresence>

      <ToastContainer toasts={toasts} onRemove={removeToast} />
      </div>
    </div>
  )
}
