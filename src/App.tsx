import { Component, type ReactNode } from 'react'
import FlipSide2 from './FlipSide2'
import './index.css'

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
    console.error('FlipSide runtime error:', error)
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'grid',
            placeItems: 'center',
            background: '#0A0804',
            color: '#F5ECD7',
            fontFamily: 'Inter, system-ui, sans-serif',
            padding: 24,
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: 560,
              borderRadius: 16,
              background: 'rgba(28,24,16,0.75)',
              border: '1px solid rgba(212,168,67,0.2)',
              padding: 24,
            }}
          >
            <h1 style={{ margin: '0 0 8px', color: '#D4A843', fontSize: 22 }}>FlipSide recovered from an error</h1>
            <p style={{ margin: '0 0 16px', color: '#9E8E6F' }}>
              The app hit a runtime issue. Refresh once. If it repeats, send this message to me:
            </p>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#F5ECD7' }}>
              {this.state.message}
            </pre>
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
      <FlipSide2 />
    </AppErrorBoundary>
  )
}

export default App
