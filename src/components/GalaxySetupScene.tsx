import { useMemo, useRef, useState, useCallback, type MutableRefObject } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Html, Sparkles, Stars } from '@react-three/drei'
import * as THREE from 'three'
import { motion, AnimatePresence } from 'framer-motion'
import type { DebateMode, Side } from '../lib/types'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

interface GalaxySetupProps {
  onSelectTopic: (topic: string) => void
  onStartDebate: (config: { topic: string; mode: DebateMode; side: Side; timerDuration: number }) => void
  presetTopics?: string[]
}

interface GenreNode {
  id: string
  label: string
  color: string
  vertex: [number, number, number]
}

interface TopicNode {
  id: string
  label: string
  genreId: string
  level: 1 | 2
  parentId?: string
  position: [number, number, number]
  collisionRadius: number
}

interface Edge {
  from: [number, number, number]
  to: [number, number, number]
  color: string
}

const GENRES = [
  { id: 'technology', label: 'Technology', color: '#8b5cf6' },
  { id: 'society', label: 'Society', color: '#42d7ff' },
  { id: 'economy', label: 'Economy', color: '#ff89d8' },
  { id: 'policy', label: 'Policy', color: '#6df0b6' },
  { id: 'science', label: 'Science', color: '#ffb86c' },
  { id: 'ethics', label: 'Ethics', color: '#df9dff' },
] as const

const KEYWORDS_BY_GENRE: Record<string, string[]> = {
  technology: ['ai', 'digital', 'software', 'crypto', 'cyber', 'platform', 'internet', 'autonomous', 'data'],
  society: ['social', 'education', 'culture', 'media', 'work', 'privacy', 'community', 'youth'],
  economy: ['market', 'tax', 'bank', 'trade', 'finance', 'income', 'labor', 'economic'],
  policy: ['government', 'regulate', 'law', 'public', 'election', 'national', 'immigration', 'security'],
  science: ['science', 'space', 'climate', 'nuclear', 'gene', 'biotech', 'health', 'environment'],
  ethics: ['ethic', 'moral', 'rights', 'justice', 'fairness', 'equity', 'responsibility'],
}

const STOP_WORDS = new Set([
  'the', 'of', 'is', 'a', 'an', 'to', 'and', 'in', 'on', 'for', 'by', 'with', 'at', 'from', 'as', 'it', 'be', 'or', 'that', 'this',
])

function rand(index: number, seed: number) {
  const value = Math.sin(index * 12.9898 + seed * 78.233) * 43758.5453
  return value - Math.floor(value)
}

function classifyGenre(topic: string) {
  const text = topic.toLowerCase()
  let bestGenre = 'society'
  let bestScore = -1
  for (const genre of GENRES) {
    const keywords = KEYWORDS_BY_GENRE[genre.id]
    let score = 0
    for (const keyword of keywords) {
      if (text.includes(keyword)) score += 1
    }
    if (score > bestScore) {
      bestScore = score
      bestGenre = genre.id
    }
  }
  return bestGenre
}

function tokenizeQuery(query: string) {
  return query
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 1 && !STOP_WORDS.has(s))
}

function bubbleCollisionRadius(text: string) {
  const short = text.length > 56 ? `${text.slice(0, 53)}...` : text
  const width = Math.max(90, Math.min(200, short.length * 4.4))
  return Math.max(1.2, width * 0.01)
}

function collides(candidate: THREE.Vector3, radius: number, placed: Array<{ p: THREE.Vector3; r: number }>) {
  for (const item of placed) {
    const minDist = radius + item.r + 0.68
    if (candidate.distanceTo(item.p) < minDist) return true
  }
  return false
}

function TopicPill({
  label,
  color,
  selected,
  onClick,
}: {
  label: string
  color: string
  selected: boolean
  onClick: () => void
}) {
  const short = label.length > 56 ? `${label.slice(0, 53)}...` : label
  const width = Math.max(90, Math.min(200, short.length * 4.4))
  return (
    <button
      onClick={onClick}
      style={{
        width,
        padding: '5px 8px',
        borderRadius: 10,
        border: `1px solid ${selected ? color : `${color}88`}`,
        background: selected ? 'rgba(24, 30, 50, 0.95)' : 'rgba(8, 12, 24, 0.86)',
        color: '#eff4ff',
        fontSize: 10,
        fontWeight: selected ? 700 : 600,
        cursor: 'pointer',
        boxShadow: selected ? `0 0 18px ${color}88` : `0 0 10px ${color}33`,
      }}
    >
      {short}
    </button>
  )
}

function GenrePill({
  label,
  color,
  active,
  onClick,
}: {
  label: string
  color: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '7px 11px',
        borderRadius: 11,
        border: `1px solid ${active ? color : `${color}66`}`,
        background: active ? 'rgba(21, 26, 43, 0.95)' : 'rgba(8, 12, 24, 0.82)',
        color: '#eef3ff',
        fontSize: 11,
        fontWeight: 700,
        cursor: 'pointer',
        boxShadow: active ? `0 0 24px ${color}88` : `0 0 9px ${color}33`,
      }}
    >
      {label}
    </button>
  )
}

function Edges({ edges }: { edges: Edge[] }) {
  const points = useMemo(() => {
    const pos = new Float32Array(edges.length * 6)
    const colors = new Float32Array(edges.length * 6)
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i]
      const c = new THREE.Color(e.color)
      const i6 = i * 6
      pos[i6] = e.from[0]
      pos[i6 + 1] = e.from[1]
      pos[i6 + 2] = e.from[2]
      pos[i6 + 3] = e.to[0]
      pos[i6 + 4] = e.to[1]
      pos[i6 + 5] = e.to[2]
      colors[i6] = c.r
      colors[i6 + 1] = c.g
      colors[i6 + 2] = c.b
      colors[i6 + 3] = c.r
      colors[i6 + 4] = c.g
      colors[i6 + 5] = c.b
    }
    return { pos, colors }
  }, [edges])

  return (
    <lineSegments>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[points.pos, 3]} />
        <bufferAttribute attach="attributes-color" args={[points.colors, 3]} />
      </bufferGeometry>
      <lineBasicMaterial vertexColors transparent opacity={0.38} />
    </lineSegments>
  )
}

function TopicNodeView({
  node,
  color,
  selected,
  onSelect,
}: {
  node: TopicNode
  color: string
  selected: boolean
  onSelect: (topic: string) => void
}) {
  return (
    <group position={node.position}>
      <mesh onClick={() => onSelect(node.label)}>
        <sphereGeometry args={[node.level === 1 ? 0.13 : 0.1, 16, 16]} />
        <meshStandardMaterial color={selected ? '#ffffff' : color} emissive={color} emissiveIntensity={selected ? 0.96 : 0.5} />
      </mesh>
      <Html transform distanceFactor={11.5} position={[0, 0.34, 0]}>
        <TopicPill label={node.label} color={color} selected={selected} onClick={() => onSelect(node.label)} />
      </Html>
    </group>
  )
}

function CameraJoystickNudge({
  controlsRef,
  joy,
}: {
  controlsRef: MutableRefObject<OrbitControlsImpl | null>
  joy: { x: number; y: number }
}) {
  const right = useMemo(() => new THREE.Vector3(), [])
  const up = useMemo(() => new THREE.Vector3(), [])
  const dir = useMemo(() => new THREE.Vector3(), [])
  const move = useMemo(() => new THREE.Vector3(), [])

  useFrame((_, delta) => {
    const controls = controlsRef.current
    if (!controls) return
    if (Math.abs(joy.x) < 0.01 && Math.abs(joy.y) < 0.01) return

    const camera = controls.object as THREE.PerspectiveCamera
    camera.getWorldDirection(dir)
    right.crossVectors(camera.up, dir).normalize()
    up.copy(camera.up).normalize()
    move
      .copy(right)
      .multiplyScalar(joy.x * delta * 10)
      .addScaledVector(up, joy.y * delta * 10)

    camera.position.add(move)
    controls.target.add(move)
    controls.update()
  })

  return null
}

function HexGenreMap({
  genres,
  activeGenreId,
  onSelect,
}: {
  genres: GenreNode[]
  activeGenreId: string
  onSelect: (genreId: string) => void
}) {
  return (
    <>
      {genres.map((g) => (
        <group key={g.id} position={g.vertex}>
          <mesh onClick={() => onSelect(g.id)}>
            <icosahedronGeometry args={[g.id === activeGenreId ? 0.56 : 0.46, 1]} />
            <meshStandardMaterial
              color={g.color}
              emissive={g.color}
              emissiveIntensity={g.id === activeGenreId ? 0.9 : 0.45}
              metalness={0.4}
              roughness={0.25}
            />
          </mesh>
          <Html transform distanceFactor={12} position={[0, 0.85, 0]}>
            <GenrePill label={g.label} color={g.color} active={g.id === activeGenreId} onClick={() => onSelect(g.id)} />
          </Html>
        </group>
      ))}
    </>
  )
}

export function GalaxySetupScene({ onSelectTopic, onStartDebate, presetTopics }: GalaxySetupProps) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null)
  const joystickRef = useRef<HTMLDivElement | null>(null)
  const [activeGenreId, setActiveGenreId] = useState<string>(GENRES[0].id)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)
  const [showConfig, setShowConfig] = useState(false)
  const [mode, setMode] = useState<DebateMode>('balanced')
  const [side, setSide] = useState<Side>('for')
  const [timerDuration, setTimerDuration] = useState(120)
  const [searchText, setSearchText] = useState('')
  const [joy, setJoy] = useState({ x: 0, y: 0, active: false })

  const safeTopics = useMemo(
    () => (Array.isArray(presetTopics) ? presetTopics.filter((t): t is string => typeof t === 'string' && t.trim().length > 0) : []),
    [presetTopics],
  )

  const genreTopics = useMemo(() => {
    const grouped: Record<string, string[]> = {}
    for (const g of GENRES) grouped[g.id] = []
    for (const topic of safeTopics) grouped[classifyGenre(topic)].push(topic)
    return grouped
  }, [safeTopics])

  const genreNodes = useMemo<GenreNode[]>(() => {
    const hexR = 13.5
    return GENRES.map((g, i) => {
      const angle = (i / 6) * Math.PI * 2 + Math.PI / 6
      return { id: g.id, label: g.label, color: g.color, vertex: [Math.cos(angle) * hexR, Math.sin(angle) * hexR, 0] }
    })
  }, [])

  const activeGenre = useMemo(() => genreNodes.find((g) => g.id === activeGenreId) ?? genreNodes[0], [activeGenreId, genreNodes])
  const activeColor = activeGenre.color

  const treeNodes = useMemo<TopicNode[]>(() => {
    const topics = (genreTopics[activeGenreId] ?? []).slice(0, 66)
    const out: TopicNode[] = []
    const placed: Array<{ p: THREE.Vector3; r: number }> = []
    const vx = activeGenre.vertex[0]
    const vy = activeGenre.vertex[1]
    const vz = activeGenre.vertex[2]
    const dir = new THREE.Vector3(vx, vy, 0).normalize()

    for (let i = 0; i < topics.length; i++) {
      const t = topics[i]
      const mainRadius = bubbleCollisionRadius(t)
      const shell = 8.6 + (i % 10) * 4.4
      let main = new THREE.Vector3(vx, vy, vz)
      let placedMain = false
      for (let tries = 0; tries < 52; tries++) {
        const theta = Math.acos(2 * rand(i * 37 + tries, 3.1) - 1)
        const phi = 2 * Math.PI * rand(i * 47 + tries, 4.7)
        const radial = shell + tries * 0.72 + Math.floor(i / 10) * 1.8
        const offset3D = new THREE.Vector3(
          radial * Math.sin(theta) * Math.cos(phi),
          radial * Math.cos(theta),
          radial * Math.sin(theta) * Math.sin(phi),
        )
        const outwardBias = dir.clone().multiplyScalar(Math.max(4.5, radial * 0.35))
        const candidate = new THREE.Vector3(vx, vy, vz)
          .add(outwardBias)
          .add(offset3D)
        if (!collides(candidate, mainRadius, placed)) {
          main = candidate
          placedMain = true
          break
        }
      }
      if (!placedMain) {
        main = new THREE.Vector3(vx, vy, vz).addScaledVector(dir, shell + 24 + i * 0.3)
      }
      placed.push({ p: main.clone(), r: mainRadius })

      out.push({
        id: `topic-${i}`,
        label: t,
        genreId: activeGenreId,
        level: 1,
        position: [main.x, main.y, main.z],
        collisionRadius: mainRadius,
      })

      if (i % 3 === 0 && i + 1 < topics.length) {
        const subCount = 1 + Math.floor(rand(i, 7.7) * 2)
        for (let s = 0; s < subCount; s++) {
          const subLabel = `${t} • focus ${s + 1}`
          const subCollision = bubbleCollisionRadius(subLabel)
          let sub = main.clone()
          let placedSub = false
          for (let tries = 0; tries < 36; tries++) {
            const parentDir = new THREE.Vector3(main.x - vx, main.y - vy, main.z - vz).normalize()
            const theta = Math.acos(2 * rand(i * 11 + s + tries, 8.8) - 1)
            const phi = 2 * Math.PI * rand(i * 13 + s + tries, 9.9)
            const subRadius = 6.6 + s * 3.6 + tries * 0.42
            const localOffset = new THREE.Vector3(
              subRadius * Math.sin(theta) * Math.cos(phi),
              subRadius * Math.cos(theta),
              subRadius * Math.sin(theta) * Math.sin(phi),
            )
            const candidateSub = main
              .clone()
              .addScaledVector(parentDir, Math.max(2.2, subRadius * 0.42))
              .add(localOffset)
            if (!collides(candidateSub, subCollision, placed)) {
              sub = candidateSub
              placedSub = true
              break
            }
          }
          if (!placedSub) {
            sub = main.clone().addScaledVector(dir, 10 + s * 3.4)
          }
          placed.push({ p: sub.clone(), r: subCollision })
          out.push({
            id: `topic-${i}-sub-${s}`,
            label: subLabel,
            genreId: activeGenreId,
            level: 2,
            parentId: `topic-${i}`,
            position: [sub.x, sub.y, sub.z],
            collisionRadius: subCollision,
          })
        }
      }
    }

    return out
  }, [activeGenre, activeGenreId, genreTopics])

  const edges = useMemo<Edge[]>(() => {
    const out: Edge[] = []
    for (const node of treeNodes) {
      if (node.level === 1) {
        out.push({ from: activeGenre.vertex, to: node.position, color: activeColor })
      } else if (node.parentId) {
        const parent = treeNodes.find((n) => n.id === node.parentId)
        if (parent) out.push({ from: parent.position, to: node.position, color: activeColor })
      }
    }
    return out
  }, [treeNodes, activeGenre.vertex, activeColor])

  const handleSelectTopic = useCallback(
    (topic: string) => {
      setSelectedTopic(topic)
      setShowConfig(true)
      onSelectTopic(topic)
    },
    [onSelectTopic],
  )

  const handleSearch = useCallback(() => {
    const tokens = tokenizeQuery(searchText)
    if (tokens.length === 0) return
    const matches = treeNodes.filter((node) => {
      const text = node.label.toLowerCase()
      return tokens.every((token) => text.includes(token))
    })
    if (matches.length === 0) return

    const target = new THREE.Vector3()
    for (const m of matches.slice(0, 6)) target.add(new THREE.Vector3(m.position[0], m.position[1], m.position[2]))
    target.divideScalar(Math.min(6, matches.length))

    const controls = controlsRef.current
    if (controls) {
      controls.target.set(target.x, target.y, target.z)
      controls.object.position.set(target.x + 6.5, target.y + 4.5, target.z + 9)
      controls.update()
    }
  }, [searchText, treeNodes])

  const handleStartDebate = useCallback(() => {
    const topic = selectedTopic
    if (!topic?.trim()) return
    onStartDebate({ topic: topic.trim(), mode, side, timerDuration })
  }, [selectedTopic, mode, side, timerDuration, onStartDebate])

  const updateJoystick = useCallback((clientX: number, clientY: number) => {
    const el = joystickRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    let x = (clientX - cx) / (rect.width / 2)
    let y = (clientY - cy) / (rect.height / 2)
    const len = Math.hypot(x, y)
    if (len > 1) {
      x /= len
      y /= len
    }
    setJoy({ x, y: -y, active: true })
  }, [])

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#03030a' }}>
      <Canvas
        camera={{ position: [0, 11, 34], fov: 48 }}
        dpr={[1, 1.2]}
        gl={{ antialias: false, alpha: false, stencil: false, depth: true, powerPreference: 'high-performance' }}
      >
        <OrbitControls ref={controlsRef} target={[0, 0, 0]} enablePan={false} minDistance={12} maxDistance={78} enableDamping dampingFactor={0.09} />
        <CameraJoystickNudge controlsRef={controlsRef} joy={joy} />
        <color attach="background" args={['#02030a']} />
        <fog attach="fog" args={['#02030a', 38, 260]} />
        <ambientLight intensity={0.32} />
        <pointLight position={[10, 12, 8]} intensity={0.76} color="#9eb4ff" />
        <pointLight position={[-10, -4, -9]} intensity={0.42} color="#54d7ff" />
        <Stars radius={230} depth={95} count={3200} factor={4.1} fade speed={0.35} saturation={0} />
        <Sparkles count={70} size={1.0} speed={0.08} scale={[62, 24, 62]} color="#98c6ff" />

        <mesh>
          <icosahedronGeometry args={[1.2, 3]} />
          <meshPhysicalMaterial color="#a389ff" emissive="#8f6cff" emissiveIntensity={0.64} roughness={0.18} metalness={0.52} />
        </mesh>

        <lineLoop>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[new Float32Array(genreNodes.flatMap((g) => [g.vertex[0], g.vertex[1], g.vertex[2]])), 3]}
            />
          </bufferGeometry>
          <lineBasicMaterial color="#96a7ec" transparent opacity={0.48} />
        </lineLoop>

        <HexGenreMap genres={genreNodes} activeGenreId={activeGenreId} onSelect={setActiveGenreId} />
        <Edges edges={edges} />
        {treeNodes.map((node) => (
          <TopicNodeView key={node.id} node={node} color={activeColor} selected={selectedTopic === node.label} onSelect={handleSelectTopic} />
        ))}
      </Canvas>

      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', display: 'flex', flexDirection: 'column', padding: 24 }}>
        <motion.div initial={{ opacity: 0, y: -14 }} animate={{ opacity: 1, y: 0 }} style={{ textAlign: 'center', pointerEvents: 'auto' }}>
          <h1
            style={{
              margin: 0,
              fontSize: 54,
              fontWeight: 800,
              letterSpacing: '0.04em',
              background: 'linear-gradient(135deg, #d3ccff, #87deff 45%, #e4b3ff)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              textShadow: '0 0 66px rgba(141, 117, 255, 0.45)',
            }}
          >
            FlipSide HexaMind
          </h1>
          <p style={{ color: 'rgba(222, 231, 255, 0.74)', marginTop: 9, fontSize: 14 }}>
            Hexagon neural map • active genre: <span style={{ color: activeColor, fontWeight: 700 }}>{activeGenre.label}</span>
          </p>
        </motion.div>

        <div
          style={{
            margin: '16px auto 0',
            pointerEvents: 'auto',
            display: 'flex',
            gap: 8,
            background: 'rgba(8, 10, 24, 0.82)',
            border: '1px solid rgba(149, 167, 255, 0.32)',
            borderRadius: 40,
            padding: '8px 10px',
            boxShadow: '0 10px 34px rgba(0,0,0,0.35)',
          }}
        >
          <input
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search topic keywords..."
            style={{
              width: 340,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#eef3ff',
              fontSize: 14,
              padding: '0 8px',
            }}
          />
          <button
            onClick={handleSearch}
            style={{
              border: 'none',
              borderRadius: 18,
              padding: '8px 14px',
              background: 'linear-gradient(135deg, #8b5cf6, #3e9fff)',
              color: '#fff',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Search
          </button>
        </div>

        <div style={{ position: 'absolute', top: 22, left: 24, pointerEvents: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap', maxWidth: 560 }}>
          {genreNodes.map((g) => (
            <GenrePill key={g.id} label={g.label} color={g.color} active={g.id === activeGenreId} onClick={() => setActiveGenreId(g.id)} />
          ))}
        </div>
      </div>

      <AnimatePresence>
        {showConfig && (
          <motion.div
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.92 }}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: 'rgba(9, 10, 20, 0.95)',
              backdropFilter: 'blur(24px)',
              padding: '32px',
              borderRadius: '24px',
              border: '1px solid rgba(137, 158, 255, 0.33)',
              minWidth: '420px',
              boxShadow: '0 22px 90px rgba(23, 29, 66, 0.6)',
            }}
          >
            <h2 style={{ color: '#fff', margin: '0 0 8px', fontSize: '24px' }}>Launch Configuration</h2>
            <p style={{ color: 'rgba(236,241,255,0.67)', margin: '0 0 24px', fontSize: '14px' }}>
              Topic: <span style={{ color: '#9ed2ff' }}>{selectedTopic}</span>
            </p>

            <div style={{ marginBottom: 20 }}>
              <label style={{ color: 'rgba(229,235,255,0.7)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Difficulty</label>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                {(['casual', 'balanced', 'intense'] as DebateMode[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    style={{
                      flex: 1,
                      padding: 12,
                      borderRadius: 12,
                      border: mode === m ? '2px solid #9bc4ff' : '1px solid rgba(255,255,255,0.2)',
                      background: mode === m ? 'rgba(140, 191, 255, 0.18)' : 'transparent',
                      color: mode === m ? '#9bc4ff' : 'rgba(255,255,255,0.65)',
                      cursor: 'pointer',
                      textTransform: 'capitalize',
                      fontWeight: 600,
                    }}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ color: 'rgba(229,235,255,0.7)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Your Side</label>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                {(['for', 'against'] as Side[]).map((s) => (
                  <button
                    key={s}
                    onClick={() => setSide(s)}
                    style={{
                      flex: 1,
                      padding: 16,
                      borderRadius: 12,
                      border: side === s ? '2px solid #77deff' : '1px solid rgba(255,255,255,0.2)',
                      background: side === s ? 'rgba(70, 205, 255, 0.14)' : 'transparent',
                      color: side === s ? '#77deff' : 'rgba(255,255,255,0.65)',
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                      fontWeight: 700,
                      fontSize: 18,
                    }}
                  >
                    {s === 'for' ? 'FOR' : 'AGAINST'}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={{ color: 'rgba(229,235,255,0.7)', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Round Timer</label>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                {[{ v: 180, l: '3 min' }, { v: 120, l: '2 min' }, { v: 90, l: '90 sec' }].map(({ v, l }) => (
                  <button
                    key={v}
                    onClick={() => setTimerDuration(v)}
                    style={{
                      flex: 1,
                      padding: 10,
                      borderRadius: 10,
                      border: timerDuration === v ? '2px solid #ffa1d8' : '1px solid rgba(255,255,255,0.2)',
                      background: timerDuration === v ? 'rgba(255, 162, 221, 0.13)' : 'transparent',
                      color: timerDuration === v ? '#ffa1d8' : 'rgba(255,255,255,0.65)',
                      cursor: 'pointer',
                      fontWeight: 600,
                    }}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: 12 }}>
              <button
                onClick={() => {
                  setShowConfig(false)
                  setSelectedTopic(null)
                }}
                style={{
                  flex: 1,
                  padding: 14,
                  borderRadius: 12,
                  border: '1px solid rgba(255,255,255,0.2)',
                  background: 'transparent',
                  color: 'rgba(255,255,255,0.72)',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Back
              </button>
              <button
                onClick={handleStartDebate}
                style={{
                  flex: 2,
                  padding: 14,
                  borderRadius: 12,
                  border: 'none',
                  background: 'linear-gradient(135deg, #8b5cf6, #4a8bff, #42d7ff)',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: 16,
                  boxShadow: '0 0 38px rgba(94, 142, 255, 0.45)',
                }}
              >
                Begin Debate
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div
        ref={joystickRef}
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId)
          updateJoystick(e.clientX, e.clientY)
        }}
        onPointerMove={(e) => {
          if (!joy.active) return
          updateJoystick(e.clientX, e.clientY)
        }}
        onPointerUp={() => setJoy({ x: 0, y: 0, active: false })}
        onPointerCancel={() => setJoy({ x: 0, y: 0, active: false })}
        style={{
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
          bottom: 28,
          width: 96,
          height: 96,
          borderRadius: '50%',
          border: '1px solid rgba(140, 168, 255, 0.48)',
          background: 'rgba(8, 12, 24, 0.65)',
          backdropFilter: 'blur(8px)',
          pointerEvents: 'auto',
          zIndex: 40,
          touchAction: 'none',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: `calc(50% + ${joy.x * 24}px - 14px)`,
            top: `calc(50% - ${joy.y * 24}px - 14px)`,
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #8b5cf6, #42d7ff)',
            boxShadow: '0 0 16px rgba(120,170,255,0.5)',
          }}
        />
      </div>
    </div>
  )
}

export default GalaxySetupScene
