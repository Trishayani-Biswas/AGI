import { type CSSProperties, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X as XIcon } from 'lucide-react'
import type { ToastMessage } from '../../lib/useToast'
import './primitives.css'

type ButtonProps = {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  fullWidth?: boolean
  disabled?: boolean
  isLoading?: boolean
  leftIcon?: ReactNode
  onClick?: () => void
  style?: CSSProperties
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled = false,
  isLoading = false,
  leftIcon,
  onClick,
  style,
}: ButtonProps) {
  const className = [
    'fsui-btn',
    `fsui-btn-${size}`,
    `fsui-btn-${variant}`,
    fullWidth ? 'fsui-btn-full' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled || isLoading}
      className={className}
      style={style}
      whileTap={{ scale: disabled || isLoading ? 1 : 0.97 }}
      whileHover={{ opacity: disabled ? 0.5 : 0.96, y: disabled ? 0 : -1 }}
    >
      {isLoading ? (
        <span className="fsui-spinner" />
      ) : (
        <>
          {leftIcon}
          {children}
        </>
      )}
    </motion.button>
  )
}

type PillProps = {
  children: ReactNode
  isSelected?: boolean
  onClick?: () => void
  size?: 'sm' | 'md'
}

export function Pill({ children, isSelected = false, onClick, size = 'md' }: PillProps) {
  const className = [
    'fsui-pill',
    `fsui-pill-${size}`,
    isSelected ? 'fsui-pill-selected' : 'fsui-pill-unselected',
  ].join(' ')

  return (
    <motion.button onClick={onClick} className={className} whileTap={{ scale: 0.97 }}>
      {children}
    </motion.button>
  )
}

type ToastProps = {
  toasts: ToastMessage[]
  onRemove: (id: string) => void
}

export function ToastContainer({ toasts, onRemove }: ToastProps) {
  return (
    <div className="fsui-toast-wrap">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className={`fsui-toast fsui-toast-${toast.type}`}
          >
            <p className="fsui-toast-text">{toast.message}</p>
            <button onClick={() => onRemove(toast.id)} className="fsui-toast-close">
              <XIcon size={16} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
