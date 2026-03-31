import { ReactNode } from 'react'
import './Hero3D.css'

interface GlassPanelProps {
  children: ReactNode
  className?: string
  variant?: 'default' | 'highlight' | 'subtle'
  glow?: boolean
}

export function GlassPanel({ children, className = '', variant = 'default', glow = false }: GlassPanelProps) {
  const variantClass = variant !== 'default' ? `glass-panel--${variant}` : ''
  const glowClass = glow ? 'glass-panel--glow' : ''
  
  return (
    <div className={`glass-panel ${variantClass} ${glowClass} ${className}`}>
      {children}
    </div>
  )
}

interface GlassButtonProps {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  className?: string
  type?: 'button' | 'submit'
}

export function GlassButton({ 
  children, 
  onClick, 
  variant = 'primary', 
  size = 'md',
  disabled = false,
  className = '',
  type = 'button'
}: GlassButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`glass-button glass-button--${variant} glass-button--${size} ${className}`}
    >
      <span className="glass-button__content">{children}</span>
      <span className="glass-button__glow" />
    </button>
  )
}

interface GlassInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  label?: string
  type?: 'text' | 'email' | 'password'
}

export function GlassInput({ value, onChange, placeholder, label, type = 'text' }: GlassInputProps) {
  return (
    <div className="glass-input-wrapper">
      {label && <label className="glass-input-label">{label}</label>}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="glass-input"
      />
    </div>
  )
}

interface GlassTextareaProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  label?: string
  rows?: number
}

export function GlassTextarea({ value, onChange, placeholder, label, rows = 4 }: GlassTextareaProps) {
  return (
    <div className="glass-input-wrapper">
      {label && <label className="glass-input-label">{label}</label>}
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className="glass-input glass-textarea"
      />
    </div>
  )
}

interface StatCardProps {
  label: string
  value: string | number
  icon?: ReactNode
  trend?: 'up' | 'down' | 'neutral'
}

export function StatCard({ label, value, icon, trend }: StatCardProps) {
  return (
    <div className="stat-card">
      {icon && <div className="stat-card__icon">{icon}</div>}
      <div className="stat-card__content">
        <span className="stat-card__value">{value}</span>
        <span className="stat-card__label">{label}</span>
      </div>
      {trend && (
        <div className={`stat-card__trend stat-card__trend--${trend}`}>
          {trend === 'up' && '↑'}
          {trend === 'down' && '↓'}
          {trend === 'neutral' && '→'}
        </div>
      )}
    </div>
  )
}

interface ProgressRingProps {
  progress: number
  size?: number
  strokeWidth?: number
  color?: string
}

export function ProgressRing({ progress, size = 80, strokeWidth = 6, color = '#8b5cf6' }: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (progress / 100) * circumference

  return (
    <div className="progress-ring-wrapper" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="progress-ring">
        <circle
          className="progress-ring__bg"
          strokeWidth={strokeWidth}
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <circle
          className="progress-ring__progress"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          r={radius}
          cx={size / 2}
          cy={size / 2}
          style={{ stroke: color }}
        />
      </svg>
      <span className="progress-ring__value">{Math.round(progress)}%</span>
    </div>
  )
}

interface ChipProps {
  children: ReactNode
  variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral'
  pulse?: boolean
}

export function Chip({ children, variant = 'neutral', pulse = false }: ChipProps) {
  return (
    <span className={`chip chip--${variant} ${pulse ? 'chip--pulse' : ''}`}>
      {pulse && <span className="chip__dot" />}
      {children}
    </span>
  )
}
