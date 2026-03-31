import { useEffect, useRef, useCallback } from 'react'
import * as THREE from 'three'

// ── types ──────────────────────────────────────────────────────────────────
interface NavState {
  up: boolean
  down: boolean
  left: boolean
  right: boolean
  orbitLeft: boolean
  orbitRight: boolean
}

// ── constants ──────────────────────────────────────────────────────────────
const STAR_COUNT = 4000
const NODE_COUNT = 24
const PAN_SPEED = 0.12
const ORBIT_SPEED = 0.008
const CIRCULAR_DRIFT_SPEED = 0.003  // subtle idle drift speed

// Galactic node colors (sharp / scientific palette)
const NODE_COLORS = [0x00f5ff, 0x7b2fff, 0xff2d7a, 0x39ff14, 0xffd700, 0xff6a00]

// ── helpers ────────────────────────────────────────────────────────────────
function buildStarField(): THREE.Points {
  const geo = new THREE.BufferGeometry()
  const positions = new Float32Array(STAR_COUNT * 3)
  const sizes = new Float32Array(STAR_COUNT)
  for (let i = 0; i < STAR_COUNT; i++) {
    const r = 600 + Math.random() * 800
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
    positions[i * 3 + 2] = r * Math.cos(phi)
    sizes[i] = 0.4 + Math.random() * 2.0
  }
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

  const mat = new THREE.PointsMaterial({
    color: 0xffffff,
    sizeAttenuation: true,
    size: 1.2,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  return new THREE.Points(geo, mat)
}

function buildCoordinateAxes(length = 120): THREE.Group {
  const group = new THREE.Group()
  group.name = 'axes'

  const axes: Array<[THREE.Vector3, number, string]> = [
    [new THREE.Vector3(length, 0, 0), 0xff3333, 'X'],
    [new THREE.Vector3(0, length, 0), 0x33ff66, 'Y'],
    [new THREE.Vector3(0, 0, length), 0x3399ff, 'Z'],
  ]

  axes.forEach(([dir, color, label]) => {
    // line
    const lineMat = new THREE.LineBasicMaterial({ color, linewidth: 2 })
    const lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), dir])
    group.add(new THREE.Line(lineGeo, lineMat))

    // cone arrowhead
    const coneGeo = new THREE.ConeGeometry(2.5, 10, 8)
    const coneMat = new THREE.MeshBasicMaterial({ color })
    const cone = new THREE.Mesh(coneGeo, coneMat)
    cone.position.copy(dir)
    if (label === 'X') cone.rotation.z = -Math.PI / 2
    if (label === 'Z') cone.rotation.x = Math.PI / 2
    group.add(cone)

    // negative half (dashed-style: shorter, dimmer)
    const negDir = dir.clone().multiplyScalar(-0.5)
    const negLineMat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.3 })
    const negLineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), negDir])
    group.add(new THREE.Line(negLineGeo, negLineMat))

    // label sprite (canvas texture)
    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 64
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = `#${color.toString(16).padStart(6, '0')}`
    ctx.font = 'bold 40px monospace'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(label, 32, 32)
    const tex = new THREE.CanvasTexture(canvas)
    const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true })
    const sprite = new THREE.Sprite(spriteMat)
    sprite.position.copy(dir.clone().multiplyScalar(1.12))
    sprite.scale.set(18, 18, 1)
    group.add(sprite)
  })

  return group
}

function buildNodes(): THREE.Group {
  const group = new THREE.Group()
  group.name = 'nodes'

  for (let i = 0; i < NODE_COUNT; i++) {
    const color = NODE_COLORS[i % NODE_COLORS.length]

    // core sphere
    const geo = new THREE.SphereGeometry(3 + Math.random() * 3, 16, 16)
    const mat = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.6,
      roughness: 0.2,
      metalness: 0.8,
    })
    const mesh = new THREE.Mesh(geo, mat)

    // random position in a large cube
    mesh.position.set(
      (Math.random() - 0.5) * 300,
      (Math.random() - 0.5) * 300,
      (Math.random() - 0.5) * 300,
    )
    mesh.userData = { baseY: mesh.position.y, phase: Math.random() * Math.PI * 2 }
    group.add(mesh)

    // glow ring
    const ringGeo = new THREE.RingGeometry(5 + Math.random() * 3, 7 + Math.random() * 3, 32)
    const ringMat = new THREE.MeshBasicMaterial({
      color,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.25,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
    const ring = new THREE.Mesh(ringGeo, ringMat)
    ring.rotation.x = Math.random() * Math.PI
    ring.rotation.y = Math.random() * Math.PI
    mesh.add(ring)
  }

  // draw edges between nearby nodes
  const positions = group.children
    .filter((c) => c instanceof THREE.Mesh)
    .map((c) => (c as THREE.Mesh).position)

  for (let i = 0; i < positions.length; i++) {
    for (let j = i + 1; j < positions.length; j++) {
      if (positions[i].distanceTo(positions[j]) < 130) {
        const lineMat = new THREE.LineBasicMaterial({
          color: 0x334466,
          transparent: true,
          opacity: 0.35,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        })
        const lineGeo = new THREE.BufferGeometry().setFromPoints([positions[i], positions[j]])
        group.add(new THREE.Line(lineGeo, lineMat))
      }
    }
  }

  return group
}

// ── component ──────────────────────────────────────────────────────────────
export default function Space3D() {
  const mountRef = useRef<HTMLDivElement>(null)
  const navRef = useRef<NavState>({
    up: false, down: false, left: false, right: false,
    orbitLeft: false, orbitRight: false,
  })
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const frameRef = useRef<number>(0)

  // button press / release helpers
  const press = useCallback((key: keyof NavState, on: boolean) => {
    navRef.current[key] = on
  }, [])

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    // ── scene ──
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x020408)
    scene.fog = new THREE.FogExp2(0x020408, 0.0008)

    // ── camera ──
    const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.5, 3000)
    camera.position.set(0, 40, 200)
    camera.lookAt(0, 0, 0)

    // camera spherical coords for orbit
    let spherical = new THREE.Spherical().setFromVector3(camera.position)

    // ── renderer ──
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // ── lighting ──
    scene.add(new THREE.AmbientLight(0x223366, 1.2))
    const pointLight1 = new THREE.PointLight(0x00aaff, 3, 600)
    pointLight1.position.set(100, 100, 100)
    scene.add(pointLight1)
    const pointLight2 = new THREE.PointLight(0xff44aa, 2, 500)
    pointLight2.position.set(-150, -80, -100)
    scene.add(pointLight2)

    // ── objects ──
    scene.add(buildStarField())
    scene.add(buildCoordinateAxes())
    const nodes = buildNodes()
    scene.add(nodes)

    // ── resize ──
    const onResize = () => {
      if (!container) return
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    window.addEventListener('resize', onResize)

    // ── mouse drag orbit ──
    let isDragging = false
    let lastMouse = { x: 0, y: 0 }

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true
      lastMouse = { x: e.clientX, y: e.clientY }
    }
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return
      const dx = e.clientX - lastMouse.x
      const dy = e.clientY - lastMouse.y
      lastMouse = { x: e.clientX, y: e.clientY }
      spherical.theta -= dx * 0.006
      spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy * 0.006))
    }
    const onMouseUp = () => { isDragging = false }

    // touch support
    let lastTouch = { x: 0, y: 0 }
    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        isDragging = true
        lastTouch = { x: e.touches[0].clientX, y: e.touches[0].clientY }
      }
    }
    const onTouchMove = (e: TouchEvent) => {
      if (!isDragging || e.touches.length !== 1) return
      const dx = e.touches[0].clientX - lastTouch.x
      const dy = e.touches[0].clientY - lastTouch.y
      lastTouch = { x: e.touches[0].clientX, y: e.touches[0].clientY }
      spherical.theta -= dx * 0.006
      spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy * 0.006))
    }
    const onTouchEnd = () => { isDragging = false }

    renderer.domElement.addEventListener('mousedown', onMouseDown)
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    renderer.domElement.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: true })
    window.addEventListener('touchend', onTouchEnd)

    // ── animation loop ──
    let t = 0
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate)
      t += 0.016

      const nav = navRef.current

      // pan camera target along world axes relative to view
      const forward = new THREE.Vector3()
      camera.getWorldDirection(forward)
      forward.y = 0
      forward.normalize()
      const right = new THREE.Vector3().crossVectors(forward, new THREE.Vector3(0, 1, 0)).normalize()

      if (nav.up)    camera.position.addScaledVector(new THREE.Vector3(0, 1, 0), PAN_SPEED * 3)
      if (nav.down)  camera.position.addScaledVector(new THREE.Vector3(0, 1, 0), -PAN_SPEED * 3)
      if (nav.left)  camera.position.addScaledVector(right, -PAN_SPEED * 3)
      if (nav.right) camera.position.addScaledVector(right, PAN_SPEED * 3)

      // orbit from buttons
      if (nav.orbitLeft)  spherical.theta -= ORBIT_SPEED * 2
      if (nav.orbitRight) spherical.theta += ORBIT_SPEED * 2

      // idle drift (slow circular orbit) when no button is held
      const anyActive = nav.up || nav.down || nav.left || nav.right || nav.orbitLeft || nav.orbitRight
      if (!anyActive && !isDragging) {
        spherical.theta += CIRCULAR_DRIFT_SPEED
      }

      // Update camera from spherical (apply pan offset)
      const target = new THREE.Vector3() // always look towards origin area
      const camOffset = new THREE.Vector3().setFromSpherical(spherical)
      camera.position.copy(target).add(camOffset)
      camera.lookAt(target)

      // gentle node float animation
      nodes.children.forEach((child) => {
        if (child instanceof THREE.Mesh && child.userData.phase !== undefined) {
          child.position.y = child.userData.baseY + Math.sin(t + child.userData.phase) * 4
          child.rotation.y = t * 0.3 + child.userData.phase
        }
      })

      renderer.render(scene, camera)
    }
    animate()

    return () => {
      cancelAnimationFrame(frameRef.current)
      window.removeEventListener('resize', onResize)
      renderer.domElement.removeEventListener('mousedown', onMouseDown)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
      renderer.domElement.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('touchmove', onTouchMove)
      window.removeEventListener('touchend', onTouchEnd)
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  // ── render ──────────────────────────────────────────────────────────────
  return (
    <div style={{ position: 'relative', width: '100%', height: '100vh', overflow: 'hidden', background: '#020408' }}>
      {/* Three.js canvas mount */}
      <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

      {/* HUD title */}
      <div style={{
        position: 'absolute', top: 20, left: '50%', transform: 'translateX(-50%)',
        color: '#00f5ff', fontFamily: 'monospace', fontSize: '1.1rem',
        letterSpacing: '0.3em', textTransform: 'uppercase',
        textShadow: '0 0 12px #00f5ff, 0 0 30px #00aaff',
        userSelect: 'none', pointerEvents: 'none',
      }}>
        ◈ ARIA · GALACTIC NODE SPACE ◈
      </div>

      {/* Axis legend */}
      <div style={{
        position: 'absolute', top: 60, left: 16,
        fontFamily: 'monospace', fontSize: '0.75rem', lineHeight: '1.8',
        userSelect: 'none', pointerEvents: 'none',
      }}>
        <span style={{ color: '#ff3333' }}>■ X — AXIS</span><br />
        <span style={{ color: '#33ff66' }}>■ Y — AXIS</span><br />
        <span style={{ color: '#3399ff' }}>■ Z — AXIS</span>
      </div>

      {/* Navigation controls */}
      <div style={{
        position: 'absolute', bottom: 28, left: '50%', transform: 'translateX(-50%)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
        userSelect: 'none',
      }}>
        {/* orbit row */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 2 }}>
          <NavBtn
            label="↺ ORBIT"
            onDown={() => press('orbitLeft', true)}
            onUp={() => press('orbitLeft', false)}
            color="#7b2fff"
          />
          <NavBtn
            label="ORBIT ↻"
            onDown={() => press('orbitRight', true)}
            onUp={() => press('orbitRight', false)}
            color="#7b2fff"
          />
        </div>

        {/* directional pad */}
        <NavBtn
          label="▲ UP"
          onDown={() => press('up', true)}
          onUp={() => press('up', false)}
        />
        <div style={{ display: 'flex', gap: 6 }}>
          <NavBtn
            label="◀ LEFT"
            onDown={() => press('left', true)}
            onUp={() => press('left', false)}
          />
          <NavBtn
            label="▶ RIGHT"
            onDown={() => press('right', true)}
            onUp={() => press('right', false)}
          />
        </div>
        <NavBtn
          label="▼ DOWN"
          onDown={() => press('down', true)}
          onUp={() => press('down', false)}
        />

        <p style={{
          color: '#334466', fontFamily: 'monospace', fontSize: '0.65rem',
          marginTop: 6, letterSpacing: '0.15em',
        }}>
          DRAG CANVAS TO ORBIT · BUTTONS TO PAN
        </p>
      </div>
    </div>
  )
}

// ── NavBtn ─────────────────────────────────────────────────────────────────
interface NavBtnProps {
  label: string
  onDown: () => void
  onUp: () => void
  color?: string
}

function NavBtn({ label, onDown, onUp, color = '#00f5ff' }: NavBtnProps) {
  return (
    <button
      onMouseDown={onDown}
      onMouseUp={onUp}
      onMouseLeave={onUp}
      onTouchStart={(e) => { e.preventDefault(); onDown() }}
      onTouchEnd={onUp}
      style={{
        background: 'rgba(0,0,0,0.55)',
        border: `1px solid ${color}`,
        color,
        fontFamily: 'monospace',
        fontSize: '0.7rem',
        letterSpacing: '0.12em',
        padding: '7px 14px',
        cursor: 'pointer',
        borderRadius: 3,
        boxShadow: `0 0 8px ${color}55`,
        textShadow: `0 0 6px ${color}`,
        minWidth: 90,
        backdropFilter: 'blur(4px)',
        transition: 'box-shadow 0.1s',
      }}
    >
      {label}
    </button>
  )
}
