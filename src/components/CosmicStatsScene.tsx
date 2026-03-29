import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Stars, Float } from '@react-three/drei'
import * as THREE from 'three'
import { motion } from 'framer-motion'
import type { DebateSession } from '../lib/types'

function rand(index: number, seed: number) {
  const value = Math.sin(index * 12.9898 + seed * 78.233) * 43758.5453
  return value - Math.floor(value)
}

interface CosmicStatsSceneProps {
  session: DebateSession
  onPlayAgain: () => void
  onExport: () => void
  onShare: () => void
}

// ============ VICTORY/DEFEAT PARTICLES ============
function ResultParticles({ isVictory }: { isVictory: boolean }) {
  const pointsRef = useRef<THREE.Points>(null)
  
  const { positions, colors } = useMemo(() => {
    const count = 500
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    
    const victoryColor = new THREE.Color('#30d158')
    const defeatColor = new THREE.Color('#ff453a')
    const baseColor = isVictory ? victoryColor : defeatColor
    
    for (let i = 0; i < count; i++) {
      const i3 = i * 3
      const radius = 10 + rand(i, 1.1) * 20
      const theta = rand(i, 2.2) * Math.PI * 2
      const phi = rand(i, 3.3) * Math.PI
      
      positions[i3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i3 + 2] = radius * Math.cos(phi)
      
      colors[i3] = baseColor.r
      colors[i3 + 1] = baseColor.g
      colors[i3 + 2] = baseColor.b
    }
    
    return { positions, colors }
  }, [isVictory])
  
  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.elapsedTime * 0.1
      pointsRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.1
    }
  })
  
  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.15}
        vertexColors
        transparent
        opacity={0.8}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

// ============ TROPHY / DEFEAT MESH ============
function ResultSymbol({ winner }: { winner: 'user' | 'ai' | 'tie' }) {
  const meshRef = useRef<THREE.Group>(null)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.3
      meshRef.current.position.y = Math.sin(state.clock.elapsedTime) * 0.3
    }
  })
  
  const color = winner === 'user' ? '#30d158' : winner === 'ai' ? '#ff453a' : '#ffcc00'
  
  return (
    <Float speed={2} rotationIntensity={0.3} floatIntensity={0.5}>
      <group ref={meshRef}>
        {winner === 'user' && (
          <>
            {/* Trophy cup */}
            <mesh position={[0, 0.5, 0]}>
              <cylinderGeometry args={[0.8, 0.5, 1.5, 32]} />
              <meshStandardMaterial
                color="#ffd700"
                emissive="#ffa500"
                emissiveIntensity={0.5}
                metalness={0.9}
                roughness={0.1}
              />
            </mesh>
            {/* Trophy base */}
            <mesh position={[0, -0.5, 0]}>
              <cylinderGeometry args={[0.3, 0.5, 0.5, 32]} />
              <meshStandardMaterial
                color="#ffd700"
                metalness={0.9}
                roughness={0.1}
              />
            </mesh>
            {/* Trophy handles */}
            <mesh position={[-1, 0.5, 0]} rotation={[0, 0, Math.PI / 4]}>
              <torusGeometry args={[0.3, 0.08, 16, 32, Math.PI]} />
              <meshStandardMaterial color="#ffd700" metalness={0.9} roughness={0.1} />
            </mesh>
            <mesh position={[1, 0.5, 0]} rotation={[0, 0, -Math.PI / 4]}>
              <torusGeometry args={[0.3, 0.08, 16, 32, Math.PI]} />
              <meshStandardMaterial color="#ffd700" metalness={0.9} roughness={0.1} />
            </mesh>
            {/* Star on top */}
            <mesh position={[0, 1.5, 0]}>
              <octahedronGeometry args={[0.3]} />
              <meshStandardMaterial
                color="#ffffff"
                emissive="#ffff00"
                emissiveIntensity={2}
              />
            </mesh>
          </>
        )}
        
        {winner === 'ai' && (
          <>
            {/* Broken shield */}
            <mesh position={[0, 0, 0]}>
              <dodecahedronGeometry args={[1.2]} />
              <meshStandardMaterial
                color="#8b0000"
                emissive="#ff0000"
                emissiveIntensity={0.3}
                metalness={0.5}
                roughness={0.7}
              />
            </mesh>
            {/* Cracks */}
            <mesh position={[0.3, 0.5, 0.8]}>
              <boxGeometry args={[0.05, 0.8, 0.05]} />
              <meshBasicMaterial color="#000" />
            </mesh>
            <mesh position={[-0.2, -0.3, 0.9]} rotation={[0, 0, 0.5]}>
              <boxGeometry args={[0.05, 0.6, 0.05]} />
              <meshBasicMaterial color="#000" />
            </mesh>
          </>
        )}
        
        {winner === 'tie' && (
          <>
            {/* Balance scales */}
            <mesh position={[0, 1, 0]}>
              <cylinderGeometry args={[0.05, 0.05, 0.1, 16]} />
              <meshStandardMaterial color="#ffd700" metalness={0.8} roughness={0.2} />
            </mesh>
            <mesh position={[0, 0.8, 0]} rotation={[0, 0, Math.PI / 2]}>
              <cylinderGeometry args={[0.03, 0.03, 2, 16]} />
              <meshStandardMaterial color="#ffd700" metalness={0.8} roughness={0.2} />
            </mesh>
            {/* Plates */}
            <mesh position={[-0.9, 0.5, 0]}>
              <cylinderGeometry args={[0.3, 0.3, 0.05, 32]} />
              <meshStandardMaterial color="#ffd700" metalness={0.8} roughness={0.2} />
            </mesh>
            <mesh position={[0.9, 0.5, 0]}>
              <cylinderGeometry args={[0.3, 0.3, 0.05, 32]} />
              <meshStandardMaterial color="#ffd700" metalness={0.8} roughness={0.2} />
            </mesh>
          </>
        )}
        
        {/* Glow */}
        <pointLight color={color} intensity={3} distance={10} />
      </group>
    </Float>
  )
}

// ============ ROUND TIMELINE PLANETS ============
function RoundTimelinePlanets({ session }: { session: DebateSession }) {
  const groupRef = useRef<THREE.Group>(null)
  
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.1
    }
  })
  
  return (
    <group ref={groupRef} position={[0, -3, 0]}>
      {session.rounds.map((round, i) => {
        const angle = (i / session.rounds.length) * Math.PI * 2
        const radius = 5
        const color = round.winner === 'user' ? '#30d158' : round.winner === 'ai' ? '#ff453a' : '#ffcc00'
        
        return (
          <mesh
            key={round.number}
            position={[Math.cos(angle) * radius, 0, Math.sin(angle) * radius]}
          >
            <sphereGeometry args={[0.3, 16, 16]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={0.5}
            />
          </mesh>
        )
      })}
      
      {/* Orbit ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[4.8, 5.2, 64]} />
        <meshBasicMaterial color="#2a2a4a" transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>
    </group>
  )
}

// ============ MAIN COSMIC STATS SCENE ============
export function CosmicStatsScene({
  session,
  onPlayAgain,
  onExport,
  onShare,
}: CosmicStatsSceneProps) {
  if (!session.verdict) return null
  
  const isVictory = session.verdict.winner === 'user'
  const isTie = session.verdict.winner === 'tie'
  
  const userWins = session.rounds.filter((r) => r.winner === 'user').length
  const totalPoints = Math.max(1, session.totalUserScore + session.totalAiScore)
  const userWinRatio = Math.round((session.totalUserScore / totalPoints) * 100)
  
  const resultColor = isVictory ? '#30d158' : isTie ? '#ffcc00' : '#ff453a'
  const resultText = isVictory ? 'VICTORY' : isTie ? 'DRAW' : 'DEFEAT'
  const resultEmoji = isVictory ? '🏆' : isTie ? '🤝' : '💫'
  
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#000' }}>
      <Canvas camera={{ position: [0, 2, 12], fov: 50 }}>
        <color attach="background" args={['#000008']} />
        <fog attach="fog" args={['#000008', 15, 50]} />
        
        {/* Lighting */}
        <ambientLight intensity={0.2} />
        <pointLight position={[10, 10, 10]} intensity={1} color={resultColor} />
        <pointLight position={[-10, -10, -10]} intensity={0.5} color="#8b5cf6" />
        
        {/* Stars */}
        <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
        
        {/* Result particles */}
        <ResultParticles isVictory={isVictory} />
        
        {/* Result symbol */}
        <ResultSymbol winner={session.verdict.winner} />
        
        {/* Round timeline */}
        <RoundTimelinePlanets session={session} />
      </Canvas>
      
      {/* UI Overlay */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          pointerEvents: 'none',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
        }}
      >
        {/* Result banner */}
        <motion.div
          initial={{ opacity: 0, scale: 0.5, y: -50 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ type: 'spring', duration: 0.8 }}
          style={{ textAlign: 'center', marginBottom: '20px' }}
        >
          <div style={{ fontSize: '60px', marginBottom: '10px' }}>{resultEmoji}</div>
          <h1
            style={{
              fontSize: '56px',
              fontWeight: 900,
              color: resultColor,
              textShadow: `0 0 60px ${resultColor}`,
              margin: 0,
              letterSpacing: '0.1em',
            }}
          >
            {resultText}
          </h1>
        </motion.div>
        
        {/* Score card */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          style={{
            background: 'rgba(10, 10, 20, 0.9)',
            backdropFilter: 'blur(20px)',
            borderRadius: '24px',
            border: `2px solid ${resultColor}40`,
            padding: '24px 40px',
            marginBottom: '24px',
            boxShadow: `0 0 40px ${resultColor}20`,
            pointerEvents: 'auto',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '40px', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.6)', marginBottom: '4px' }}>YOU</div>
              <div style={{ fontSize: '48px', fontWeight: 800, color: '#8b5cf6' }}>{session.totalUserScore}</div>
            </div>
            <div style={{ fontSize: '24px', color: 'rgba(255,255,255,0.3)' }}>vs</div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.6)', marginBottom: '4px' }}>FLIPSIDE</div>
              <div style={{ fontSize: '48px', fontWeight: 800, color: '#ff6b6b' }}>{session.totalAiScore}</div>
            </div>
          </div>
          
          {/* Progress bar */}
          <div style={{ marginTop: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>Performance</span>
              <span style={{ fontSize: '12px', color: resultColor, fontWeight: 700 }}>{userWinRatio}%</span>
            </div>
            <div style={{ height: '8px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${userWinRatio}%` }}
                transition={{ delay: 0.5, duration: 1, ease: 'easeOut' }}
                style={{
                  height: '100%',
                  background: `linear-gradient(90deg, #8b5cf6, ${resultColor})`,
                  borderRadius: '4px',
                }}
              />
            </div>
          </div>
        </motion.div>
        
        {/* Stats grid */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          style={{
            display: 'flex',
            gap: '16px',
            marginBottom: '24px',
            pointerEvents: 'auto',
          }}
        >
          {[
            { label: 'Rounds Won', value: userWins, color: '#30d158' },
            { label: 'Arguments', value: session.messages.filter((m) => m.role === 'user').length, color: '#8b5cf6' },
            { label: 'Difficulty', value: session.mode, color: '#00ffff' },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.6 + i * 0.1 }}
              style={{
                background: 'rgba(10, 10, 20, 0.8)',
                backdropFilter: 'blur(10px)',
                borderRadius: '16px',
                border: `1px solid ${stat.color}40`,
                padding: '16px 24px',
                textAlign: 'center',
                minWidth: '120px',
              }}
            >
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase', marginBottom: '4px' }}>
                {stat.label}
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: stat.color, textTransform: 'capitalize' }}>
                {stat.value}
              </div>
            </motion.div>
          ))}
        </motion.div>
        
        {/* Verdict summary */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          style={{
            maxWidth: '500px',
            textAlign: 'center',
            marginBottom: '24px',
            pointerEvents: 'auto',
          }}
        >
          <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: '16px', lineHeight: 1.6 }}>
            {session.verdict.summary}
          </p>
        </motion.div>
        
        {/* Action buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1 }}
          style={{
            display: 'flex',
            gap: '12px',
            pointerEvents: 'auto',
          }}
        >
          <button
            onClick={onExport}
            style={{
              padding: '14px 28px',
              borderRadius: '14px',
              border: '1px solid rgba(255,255,255,0.2)',
              background: 'rgba(255,255,255,0.05)',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '15px',
              transition: 'all 0.2s',
            }}
          >
            📄 Export
          </button>
          <button
            onClick={onShare}
            style={{
              padding: '14px 28px',
              borderRadius: '14px',
              border: '1px solid rgba(139, 92, 246, 0.3)',
              background: 'rgba(139, 92, 246, 0.15)',
              color: '#8b5cf6',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '15px',
              transition: 'all 0.2s',
            }}
          >
            🔗 Share
          </button>
          <button
            onClick={onPlayAgain}
            style={{
              padding: '14px 36px',
              borderRadius: '14px',
              border: 'none',
              background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '15px',
              boxShadow: '0 0 30px rgba(139, 92, 246, 0.4)',
              transition: 'all 0.2s',
            }}
          >
            🚀 Debate Again
          </button>
        </motion.div>
      </div>
    </div>
  )
}

export default CosmicStatsScene
