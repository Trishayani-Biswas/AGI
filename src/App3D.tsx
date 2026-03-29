import { Component, type ReactNode, Suspense } from 'react'
import FlipSide3D from './FlipSide3D'
import './index.css'

// Loading screen for 3D assets
function LoadingScreen() {
  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        background: 'radial-gradient(ellipse at center, #1a1a2e 0%, #000 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <div
        style={{
          width: 80,
          height: 80,
          border: '3px solid rgba(139, 92, 246, 0.2)',
          borderTop: '3px solid #8b5cf6',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
          marginBottom: 24,
        }}
      />
      <h1
        style={{
          fontSize: 32,
          fontWeight: 800,
          background: 'linear-gradient(135deg, #8b5cf6, #00ffff)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          margin: '0 0 8px',
        }}
      >
        FlipSide
      </h1>
      <p style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: 14 }}>
        Initializing galaxy...
      </p>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

// Error boundary for catching 3D rendering errors
interface ErrorBoundaryState {
  hasError: boolean
  message: string
}

class AppErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    hasError: false,
    message: '',
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message || 'Unknown error' }
  }

  override componentDidCatch(error: Error): void {
    console.error('FlipSide 3D runtime error:', error)
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'radial-gradient(ellipse at center, #1a1a2e 0%, #000 100%)',
            color: '#fff',
            fontFamily: 'Inter, system-ui, sans-serif',
            padding: 24,
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: 500,
              borderRadius: 24,
              background: 'rgba(20, 20, 40, 0.9)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255, 69, 58, 0.3)',
              padding: 32,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 48, marginBottom: 16 }}>🌌</div>
            <h1 style={{ margin: '0 0 12px', color: '#ff453a', fontSize: 24, fontWeight: 700 }}>
              Houston, we have a problem
            </h1>
            <p style={{ margin: '0 0 20px', color: 'rgba(255, 255, 255, 0.7)', lineHeight: 1.6 }}>
              The 3D galaxy encountered an error. This might be due to WebGL compatibility.
            </p>
            <pre
              style={{
                margin: '0 0 20px',
                padding: 16,
                borderRadius: 12,
                background: 'rgba(0, 0, 0, 0.4)',
                color: '#ff6b6b',
                fontSize: 12,
                textAlign: 'left',
                overflow: 'auto',
                maxHeight: 150,
              }}
            >
              {this.state.message}
            </pre>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: '12px 32px',
                borderRadius: 12,
                border: 'none',
                background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
                color: '#fff',
                fontSize: 16,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🔄 Retry Launch
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  return (
    <AppErrorBoundary>
      <Suspense fallback={<LoadingScreen />}>
        <FlipSide3D />
      </Suspense>
    </AppErrorBoundary>
  )
}

export default App
