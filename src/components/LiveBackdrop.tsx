import { useEffect, useRef } from 'react'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  r: number
}

export function LiveBackdrop() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const context = canvas.getContext('2d')
    if (!context) return

    let animationId = 0
    let width = 0
    let height = 0
    const pointer = { x: 0, y: 0, active: false }

    const particles: Particle[] = []

    const resize = () => {
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = Math.floor(width * window.devicePixelRatio)
      canvas.height = Math.floor(height * window.devicePixelRatio)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      context.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0)

      const targetCount = Math.max(24, Math.floor((width * height) / 70000))
      particles.length = 0
      for (let i = 0; i < targetCount; i += 1) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          r: Math.random() * 1.6 + 0.7
        })
      }
    }

    const onPointerMove = (event: MouseEvent) => {
      pointer.x = event.clientX
      pointer.y = event.clientY
      pointer.active = true
    }

    const onPointerLeave = () => {
      pointer.active = false
    }

    const draw = () => {
      context.clearRect(0, 0, width, height)

      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy

        if (p.x < -10) p.x = width + 10
        if (p.x > width + 10) p.x = -10
        if (p.y < -10) p.y = height + 10
        if (p.y > height + 10) p.y = -10
      }

      for (let i = 0; i < particles.length; i += 1) {
        const a = particles[i]

        for (let j = i + 1; j < particles.length; j += 1) {
          const b = particles[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const distance = Math.hypot(dx, dy)

          if (distance < 120) {
            const alpha = (1 - distance / 120) * 0.2
            context.strokeStyle = `rgba(129, 198, 255, ${alpha})`
            context.lineWidth = 1
            context.beginPath()
            context.moveTo(a.x, a.y)
            context.lineTo(b.x, b.y)
            context.stroke()
          }
        }
      }

      if (pointer.active) {
        for (const p of particles) {
          const dx = pointer.x - p.x
          const dy = pointer.y - p.y
          const distance = Math.hypot(dx, dy)

          if (distance < 150 && distance > 1) {
            p.vx -= (dx / distance) * 0.0008
            p.vy -= (dy / distance) * 0.0008
            context.strokeStyle = `rgba(255, 183, 132, ${(1 - distance / 150) * 0.28})`
            context.lineWidth = 1
            context.beginPath()
            context.moveTo(p.x, p.y)
            context.lineTo(pointer.x, pointer.y)
            context.stroke()
          }
        }
      }

      for (const p of particles) {
        context.fillStyle = 'rgba(199, 233, 255, 0.75)'
        context.beginPath()
        context.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        context.fill()
      }

      animationId = window.requestAnimationFrame(draw)
    }

    resize()
    draw()

    window.addEventListener('resize', resize)
    window.addEventListener('mousemove', onPointerMove)
    window.addEventListener('mouseleave', onPointerLeave)

    return () => {
      window.cancelAnimationFrame(animationId)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onPointerMove)
      window.removeEventListener('mouseleave', onPointerLeave)
    }
  }, [])

  return <canvas ref={canvasRef} className="live-backdrop" aria-hidden="true" />
}
