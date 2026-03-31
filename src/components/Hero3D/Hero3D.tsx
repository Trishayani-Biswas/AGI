import { Suspense, useState, useRef, useEffect, FormEvent } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera, Environment } from '@react-three/drei'
import gsap from 'gsap'
import { Scene3D } from './Scene3D'
import { GlassPanel, GlassButton, GlassInput, GlassTextarea, StatCard, ProgressRing, Chip } from './GlassComponents'
import './Hero3D.css'

interface Hero3DProps {
  onStartResearch?: (topic: string, query: string) => void
  isSubmitting?: boolean
  backendOnline?: boolean
  statusText?: string
  progress?: number
  confidence?: string
  findings?: number
}

function LoadingFallback() {
  return (
    <div className="hero-loading">
      <div className="hero-loading__spinner" />
      <p>Initializing 3D environment...</p>
    </div>
  )
}

export function Hero3D({
  onStartResearch,
  isSubmitting = false,
  backendOnline = false,
  statusText = 'Idle',
  progress = 0,
  confidence = '--',
  findings = 0
}: Hero3DProps) {
  const [topic, setTopic] = useState('')
  const [query, setQuery] = useState('')
  const [activeSection, setActiveSection] = useState<'hero' | 'control'>('hero')
  
  const heroRef = useRef<HTMLDivElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const subtitleRef = useRef<HTMLParagraphElement>(null)
  const panelsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (titleRef.current && subtitleRef.current && panelsRef.current) {
      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
      
      tl.fromTo(titleRef.current, 
        { opacity: 0, y: 60, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: 1.2 }
      )
      .fromTo(subtitleRef.current,
        { opacity: 0, y: 40 },
        { opacity: 1, y: 0, duration: 0.8 },
        '-=0.6'
      )
      .fromTo(panelsRef.current.children,
        { opacity: 0, y: 50, scale: 0.9 },
        { opacity: 1, y: 0, scale: 1, duration: 0.6, stagger: 0.15 },
        '-=0.4'
      )
    }
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (onStartResearch && topic.trim() && query.trim()) {
      onStartResearch(topic.trim(), query.trim())
    }
  }

  const scrollToControl = () => {
    setActiveSection('control')
    gsap.to(window, { duration: 0.8, scrollTo: '#control-surface', ease: 'power2.inOut' })
  }

  return (
    <div className="hero-3d" ref={heroRef}>
      <div className="hero-3d__canvas">
        <Canvas dpr={[1, 2]} gl={{ antialias: true, alpha: true }}>
          <Suspense fallback={null}>
            <PerspectiveCamera makeDefault position={[0, 0, 8]} fov={50} />
            <Scene3D />
            <OrbitControls
              enableZoom={false}
              enablePan={false}
              maxPolarAngle={Math.PI / 1.8}
              minPolarAngle={Math.PI / 3}
              autoRotate
              autoRotateSpeed={0.3}
            />
            <Environment preset="night" />
          </Suspense>
        </Canvas>
      </div>

      <div className="hero-3d__overlay">
        <nav className="hero-nav">
          <div className="hero-nav__brand">
            <span className="hero-nav__logo">◈</span>
            <span className="hero-nav__name">ARIA</span>
          </div>
          <div className="hero-nav__links">
            <a href="#stage" className="hero-nav__link">Stage</a>
            <a href="#control-surface" className="hero-nav__link">Control</a>
            <a href="#evidence" className="hero-nav__link">Evidence</a>
            <a href="#archive" className="hero-nav__link">Archive</a>
          </div>
          <div className="hero-nav__status">
            <Chip variant={backendOnline ? 'success' : 'error'} pulse>
              {backendOnline ? 'Online' : 'Offline'}
            </Chip>
          </div>
        </nav>

        <main className="hero-content">
          <div className="hero-content__text">
            <p className="hero-eyebrow">MULTI-AGENT DECISION FABRIC</p>
            <h1 ref={titleRef} className="hero-title">
              <span className="hero-title__line">Where Ideas</span>
              <span className="hero-title__line hero-title__gradient">Compete</span>
              <span className="hero-title__line">& Converge</span>
            </h1>
            <p ref={subtitleRef} className="hero-subtitle">
              A studio-grade surface where competing arguments are generated, 
              challenged, and resolved into one synthesis that carries 
              confidence and traceability.
            </p>
            <div className="hero-cta">
              <GlassButton variant="primary" size="lg" onClick={scrollToControl}>
                Launch Research
              </GlassButton>
              <GlassButton variant="ghost" size="lg">
                Learn More
              </GlassButton>
            </div>
          </div>

          <div ref={panelsRef} className="hero-panels">
            <GlassPanel variant="highlight" glow className="hero-stat-panel">
              <div className="hero-stat-panel__header">
                <h3>System Status</h3>
                <Chip variant={statusText === 'Running' ? 'warning' : 'info'}>
                  {statusText}
                </Chip>
              </div>
              <div className="hero-stat-panel__grid">
                <StatCard label="Confidence" value={confidence} />
                <StatCard label="Findings" value={findings} />
              </div>
              <div className="hero-stat-panel__progress">
                <ProgressRing progress={progress} size={100} color="#8b5cf6" />
              </div>
            </GlassPanel>

            <GlassPanel className="hero-info-panel">
              <h3>How It Works</h3>
              <div className="hero-steps">
                <div className="hero-step">
                  <span className="hero-step__num">01</span>
                  <div className="hero-step__content">
                    <h4>Frame</h4>
                    <p>Define topic boundaries</p>
                  </div>
                </div>
                <div className="hero-step">
                  <span className="hero-step__num">02</span>
                  <div className="hero-step__content">
                    <h4>Contest</h4>
                    <p>Parallel agent analysis</p>
                  </div>
                </div>
                <div className="hero-step">
                  <span className="hero-step__num">03</span>
                  <div className="hero-step__content">
                    <h4>Resolve</h4>
                    <p>Synthesize & score</p>
                  </div>
                </div>
              </div>
            </GlassPanel>
          </div>
        </main>

        <section id="control-surface" className="control-section">
          <div className="control-section__inner">
            <GlassPanel variant="highlight" className="control-panel">
              <div className="control-panel__header">
                <p className="control-eyebrow">CONTROL SURFACE</p>
                <h2>Start a Research Run</h2>
              </div>
              <form className="control-form" onSubmit={handleSubmit}>
                <GlassInput
                  label="Topic"
                  value={topic}
                  onChange={setTopic}
                  placeholder="Example: Carbon removal policy"
                />
                <GlassTextarea
                  label="Research Query"
                  value={query}
                  onChange={setQuery}
                  placeholder="Define the exact claim or decision that requires adversarial analysis."
                  rows={4}
                />
                <GlassButton 
                  type="submit" 
                  variant="primary" 
                  size="lg" 
                  disabled={isSubmitting || !topic.trim() || !query.trim()}
                >
                  {isSubmitting ? 'Starting...' : 'Start ARIA Run'}
                </GlassButton>
              </form>
            </GlassPanel>

            <GlassPanel className="telemetry-panel">
              <div className="telemetry-panel__header">
                <p className="control-eyebrow">TELEMETRY FEED</p>
                <h2>Session Stream</h2>
              </div>
              <div className="telemetry-feed">
                <div className="telemetry-item">
                  <span className="telemetry-item__label">Status</span>
                  <span className="telemetry-item__value">{statusText}</span>
                </div>
                <div className="telemetry-item">
                  <span className="telemetry-item__label">Confidence</span>
                  <span className="telemetry-item__value">{confidence}</span>
                </div>
                <div className="telemetry-item">
                  <span className="telemetry-item__label">Findings</span>
                  <span className="telemetry-item__value">{findings}</span>
                </div>
              </div>
              <div className="telemetry-synthesis">
                <h3>Arbitrator Synthesis</h3>
                <p>Synthesis appears once all agent streams converge.</p>
              </div>
            </GlassPanel>
          </div>
        </section>
      </div>

      <div className="hero-scroll-indicator">
        <span>Scroll to explore</span>
        <div className="hero-scroll-indicator__arrow">↓</div>
      </div>
    </div>
  )
}

export default Hero3D
