import { Component, type ReactNode, Suspense } from 'react'
import FlipSide3D from './FlipSide3D'
import './index.css'
import './FlipSide3d.css'

// Loading screen for 3D assets
function LoadingScreen() {
  return (
    <div className="fs3d-app-loading">
      <div className="fs3d-app-loading-spinner" />
      <h1 className="fs3d-app-loading-title">
        FlipSide
      </h1>
      <p className="fs3d-app-loading-subtitle">
        Initializing galaxy...
      </p>
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
        <div className="fs3d-app-error-shell">
          <div className="fs3d-app-error-card">
            <div className="fs3d-app-error-icon">🌌</div>
            <h1 className="fs3d-app-error-title">
              Houston, we have a problem
            </h1>
            <p className="fs3d-app-error-copy">
              The 3D galaxy encountered an error. This might be due to WebGL compatibility.
            </p>
            <pre className="fs3d-app-error-stack">
              {this.state.message}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="fs3d-app-error-retry"
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
