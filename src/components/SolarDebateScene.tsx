import { useRef, useMemo, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, Stars, Html, Trail } from '@react-three/drei'
import * as THREE from 'three'
import { motion, AnimatePresence } from 'framer-motion'
import type { DebateSession, Message, Round } from '../lib/types'

// ============ TYPES ============
interface SolarDebateSceneProps {
  session: DebateSession
  currentRound: number
  totalRounds: number
  isAiThinking: boolean
  timeRemaining: number
  timerDuration: number
  onSendMessage: (content: string, responseTime: number, timerDuration: number) => Promise<void>
  onBack: () => void
}

function rand(index: number, seed: number) {
  const value = Math.sin(index * 12.9898 + seed * 78.233) * 43758.5453
  return value - Math.floor(value)
}

// ============ SUN (TOPIC CENTER) ============
function TopicSun({ topic, pulseIntensity = 1 }: { topic: string; pulseIntensity?: number }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.002
      const pulse = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.05 * pulseIntensity
      meshRef.current.scale.setScalar(pulse)
    }
    if (glowRef.current) {
      glowRef.current.rotation.y -= 0.001
      const glowPulse = 1 + Math.sin(state.clock.elapsedTime * 1.5) * 0.1
      glowRef.current.scale.setScalar(glowPulse * 1.5)
    }
  })
  
  return (
    <group>
      {/* Core sun */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[2, 64, 64]} />
        <meshStandardMaterial
          color="#ff6b35"
          emissive="#ff4500"
          emissiveIntensity={2}
          metalness={0.1}
          roughness={0.8}
        />
      </mesh>
      
      {/* Inner glow */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[2.2, 32, 32]} />
        <meshBasicMaterial
          color="#ffaa00"
          transparent
          opacity={0.3}
          side={THREE.BackSide}
        />
      </mesh>
      
      {/* Outer glow */}
      <mesh>
        <sphereGeometry args={[3, 32, 32]} />
        <meshBasicMaterial
          color="#ff6b35"
          transparent
          opacity={0.1}
          side={THREE.BackSide}
        />
      </mesh>
      
      {/* Corona rays */}
      {[...Array(8)].map((_, i) => (
        <mesh key={i} rotation={[0, (i / 8) * Math.PI * 2, 0]}>
          <coneGeometry args={[0.3, 3, 8]} />
          <meshBasicMaterial color="#ffcc00" transparent opacity={0.2} />
        </mesh>
      ))}
      
      {/* Topic label */}
      <Html center position={[0, 4, 0]} distanceFactor={15}>
        <div
          style={{
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(10px)',
            padding: '12px 24px',
            borderRadius: '30px',
            border: '2px solid #ff6b35',
            color: '#fff',
            fontSize: '18px',
            fontWeight: 700,
            whiteSpace: 'nowrap',
            textAlign: 'center',
            boxShadow: '0 0 40px rgba(255, 107, 53, 0.5)',
          }}
        >
          🎯 {topic}
        </div>
      </Html>
      
      {/* Sun light */}
      <pointLight color="#ff6b35" intensity={3} distance={50} decay={2} />
      <pointLight color="#ffcc00" intensity={1} distance={30} decay={2} />
    </group>
  )
}

// ============ PLANET (ROUND) ============
function RoundPlanet({
  round,
  index,
  totalRounds,
  isCurrentRound,
  isCompleted,
}: {
  round?: Round
  index: number
  totalRounds: number
  isCurrentRound: boolean
  isCompleted: boolean
}) {
  const groupRef = useRef<THREE.Group>(null)
  const planetRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)
  
  // Calculate orbital position
  const orbitRadius = 6 + index * 2.5
  const orbitSpeed = 0.1 / (index + 1)
  const initialAngle = (index / totalRounds) * Math.PI * 2
  
  // Planet appearance based on state
  const planetColor = isCompleted
    ? round?.winner === 'user' ? '#30d158' : round?.winner === 'ai' ? '#ff453a' : '#ffcc00'
    : isCurrentRound ? '#00ffff' : '#4a4a6a'
  
  const planetSize = 0.4 + (isCurrentRound ? 0.2 : 0)
  
  useFrame((state) => {
    if (groupRef.current) {
      const angle = initialAngle + state.clock.elapsedTime * orbitSpeed
      groupRef.current.position.x = Math.cos(angle) * orbitRadius
      groupRef.current.position.z = Math.sin(angle) * orbitRadius
      groupRef.current.position.y = Math.sin(angle * 2) * 0.5
    }
    if (planetRef.current) {
      planetRef.current.rotation.y += 0.02
    }
  })
  
  return (
    <group ref={groupRef}>
      {/* Orbit ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <ringGeometry args={[orbitRadius - 0.02, orbitRadius + 0.02, 128]} />
        <meshBasicMaterial
          color={isCurrentRound ? '#00ffff' : '#2a2a4a'}
          transparent
          opacity={isCurrentRound ? 0.5 : 0.2}
          side={THREE.DoubleSide}
        />
      </mesh>
      
      <Float speed={2} rotationIntensity={0.1} floatIntensity={0.2}>
        <Trail
          width={isCurrentRound ? 1 : 0.3}
          length={6}
          color={planetColor}
          attenuation={(t) => t * t}
        >
          <mesh
            ref={planetRef}
            onPointerOver={() => setHovered(true)}
            onPointerOut={() => setHovered(false)}
          >
            <sphereGeometry args={[planetSize, 32, 32]} />
            <meshStandardMaterial
              color={planetColor}
              emissive={planetColor}
              emissiveIntensity={isCurrentRound ? 1 : 0.3}
              metalness={0.3}
              roughness={0.6}
            />
          </mesh>
        </Trail>
        
        {/* Planet glow */}
        {isCurrentRound && (
          <mesh>
            <sphereGeometry args={[planetSize * 1.5, 16, 16]} />
            <meshBasicMaterial color="#00ffff" transparent opacity={0.15} />
          </mesh>
        )}
        
        {/* Ring for current planet */}
        {isCurrentRound && (
          <mesh rotation={[Math.PI / 3, 0, 0]}>
            <ringGeometry args={[planetSize * 1.3, planetSize * 1.8, 32]} />
            <meshBasicMaterial color="#00ffff" transparent opacity={0.4} side={THREE.DoubleSide} />
          </mesh>
        )}
        
        {/* Moon (score indicator) */}
        {isCompleted && round && (
          <group>
            <mesh position={[planetSize + 0.5, 0.3, 0]}>
              <sphereGeometry args={[0.12, 16, 16]} />
              <meshStandardMaterial
                color="#ffffff"
                emissive="#ffffff"
                emissiveIntensity={0.5}
              />
            </mesh>
          </group>
        )}
        
        {/* Label */}
        {(hovered || isCurrentRound) && (
          <Html center position={[0, planetSize + 0.8, 0]} distanceFactor={8}>
            <div
              style={{
                background: 'rgba(0, 0, 0, 0.9)',
                backdropFilter: 'blur(10px)',
                padding: '8px 16px',
                borderRadius: '16px',
                border: `2px solid ${planetColor}`,
                color: '#fff',
                fontSize: '13px',
                fontWeight: 600,
                whiteSpace: 'nowrap',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '16px', marginBottom: '4px' }}>
                Round {index + 1}
              </div>
              {isCompleted && round && (
                <div style={{ fontSize: '11px', opacity: 0.8 }}>
                  {round.winner === 'user' ? '🏆 You Won' : round.winner === 'ai' ? '🤖 AI Won' : '🤝 Tie'}
                  <br />
                  Score: {round.userScore} - {round.aiScore}
                </div>
              )}
              {isCurrentRound && !isCompleted && (
                <div style={{ color: '#00ffff', fontSize: '11px' }}>⚡ ACTIVE</div>
              )}
            </div>
          </Html>
        )}
      </Float>
    </group>
  )
}

// ============ ASTEROID BELT (MESSAGES) ============
function MessageAsteroids({ messages }: { messages: Message[] }) {
  const groupRef = useRef<THREE.Group>(null)
  
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.05
    }
  })
  
  const asteroids = useMemo(() => {
    return messages.slice(-20).map((msg, i) => {
      const seedBase = i + msg.id.length
      const angle = (i / 20) * Math.PI * 2 + rand(seedBase, 1.9) * 0.5
      const radius = 18 + rand(seedBase, 2.7) * 3
      const height = (rand(seedBase, 3.5) - 0.5) * 2
      const size = 0.15 + rand(seedBase, 4.3) * 0.1
      const color = msg.role === 'user' ? '#8b5cf6' : '#ff6b6b'
      
      return { id: msg.id, angle, radius, height, size, color, content: msg.content }
    })
  }, [messages])
  
  return (
    <group ref={groupRef}>
      {asteroids.map((asteroid) => (
        <mesh
          key={asteroid.id}
          position={[
            Math.cos(asteroid.angle) * asteroid.radius,
            asteroid.height,
            Math.sin(asteroid.angle) * asteroid.radius,
          ]}
        >
          <dodecahedronGeometry args={[asteroid.size]} />
          <meshStandardMaterial
            color={asteroid.color}
            emissive={asteroid.color}
            emissiveIntensity={0.3}
            metalness={0.5}
            roughness={0.5}
          />
        </mesh>
      ))}
    </group>
  )
}

// ============ MAIN SOLAR DEBATE SCENE ============
export function SolarDebateScene({
  session,
  currentRound,
  totalRounds,
  isAiThinking,
  timeRemaining,
  timerDuration,
  onSendMessage,
  onBack,
}: SolarDebateSceneProps) {
  const [inputValue, setInputValue] = useState('')
  const [showMessages, setShowMessages] = useState(false)
  
  const handleSubmit = async () => {
    const content = inputValue.trim()
    if (!content || isAiThinking) return
    
    const responseTime = Math.max(0, timerDuration - timeRemaining)
    setInputValue('')
    await onSendMessage(content, responseTime, timerDuration)
  }
  
  // Timer display
  const minutes = Math.floor(timeRemaining / 60)
  const seconds = timeRemaining % 60
  const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`
  const isWarning = timeRemaining <= 15
  
  // Score calculation
  const userWins = session.rounds.filter((r) => r.winner === 'user').length
  const aiWins = session.rounds.filter((r) => r.winner === 'ai').length
  
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#000' }}>
      <Canvas camera={{ position: [0, 12, 25], fov: 50 }}>
        <color attach="background" args={['#000005']} />
        <fog attach="fog" args={['#000005', 30, 100]} />
        
        {/* Lighting */}
        <ambientLight intensity={0.1} />
        
        {/* Stars background */}
        <Stars radius={150} depth={60} count={7000} factor={5} saturation={0} fade speed={0.5} />
        
        {/* Topic Sun at center */}
        <TopicSun topic={session.topic} pulseIntensity={isAiThinking ? 2 : 1} />
        
        {/* Round planets orbiting */}
        {[...Array(totalRounds)].map((_, i) => (
          <RoundPlanet
            key={i}
            round={session.rounds[i]}
            index={i}
            totalRounds={totalRounds}
            isCurrentRound={i + 1 === currentRound}
            isCompleted={session.rounds.some((r) => r.number === i + 1)}
          />
        ))}
        
        {/* Message asteroids */}
        <MessageAsteroids messages={session.messages} />
        
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
        }}
      >
        {/* Top bar */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 24px',
            pointerEvents: 'auto',
          }}
        >
          {/* Back button */}
          <button
            onClick={onBack}
            style={{
              background: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '12px',
              padding: '10px 16px',
              color: '#fff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            ← Back
          </button>
          
          {/* Timer */}
          <motion.div
            animate={isWarning ? { scale: [1, 1.05, 1] } : {}}
            transition={{ repeat: Infinity, duration: 0.5 }}
            style={{
              background: isWarning
                ? 'linear-gradient(135deg, rgba(255, 69, 58, 0.3), rgba(255, 149, 0, 0.3))'
                : 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(10px)',
              border: `2px solid ${isWarning ? '#ff453a' : 'rgba(255, 255, 255, 0.2)'}`,
              borderRadius: '20px',
              padding: '12px 24px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <span style={{ fontSize: '14px', color: 'rgba(255,255,255,0.7)' }}>
              Round {currentRound}/{totalRounds}
            </span>
            <span
              style={{
                fontSize: '28px',
                fontWeight: 700,
                color: isWarning ? '#ff453a' : '#00ffff',
                fontFamily: 'monospace',
              }}
            >
              {timeString}
            </span>
          </motion.div>
          
          {/* Score */}
          <div
            style={{
              background: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '16px',
              padding: '10px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)', textTransform: 'uppercase' }}>You</div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: '#8b5cf6' }}>{session.totalUserScore}</div>
              <div style={{ fontSize: '10px', color: '#30d158' }}>🏆 {userWins}</div>
            </div>
            <div style={{ width: '1px', height: '40px', background: 'rgba(255,255,255,0.2)' }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)', textTransform: 'uppercase' }}>AI</div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: '#ff6b6b' }}>{session.totalAiScore}</div>
              <div style={{ fontSize: '10px', color: '#ff453a' }}>🤖 {aiWins}</div>
            </div>
          </div>
        </div>
        
        {/* Messages panel toggle */}
        <button
          onClick={() => setShowMessages(!showMessages)}
          style={{
            position: 'absolute',
            right: '24px',
            top: '80px',
            background: 'rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(139, 92, 246, 0.3)',
            borderRadius: '12px',
            padding: '10px 16px',
            color: '#8b5cf6',
            cursor: 'pointer',
            pointerEvents: 'auto',
          }}
        >
          {showMessages ? '✕ Hide' : '💬 Messages'} ({session.messages.length})
        </button>
        
        {/* Messages panel */}
        <AnimatePresence>
          {showMessages && (
            <motion.div
              initial={{ opacity: 0, x: 300 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 300 }}
              style={{
                position: 'absolute',
                right: '24px',
                top: '130px',
                bottom: '150px',
                width: '380px',
                background: 'rgba(10, 10, 20, 0.95)',
                backdropFilter: 'blur(20px)',
                borderRadius: '20px',
                border: '1px solid rgba(139, 92, 246, 0.3)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                pointerEvents: 'auto',
              }}
            >
              <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <h3 style={{ margin: 0, color: '#fff', fontSize: '16px' }}>Debate Exchange</h3>
              </div>
              <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
                {session.messages.map((msg) => (
                  <div
                    key={msg.id}
                    style={{
                      marginBottom: '12px',
                      padding: '12px',
                      borderRadius: '12px',
                      background: msg.role === 'user'
                        ? 'rgba(139, 92, 246, 0.15)'
                        : 'rgba(255, 107, 107, 0.1)',
                      borderLeft: `3px solid ${msg.role === 'user' ? '#8b5cf6' : '#ff6b6b'}`,
                    }}
                  >
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>
                      {msg.role === 'user' ? '👤 You' : '🤖 FlipSide'} • Round {msg.roundNumber}
                    </div>
                    <p style={{ margin: 0, color: '#fff', fontSize: '14px', lineHeight: 1.5 }}>
                      {msg.content}
                    </p>
                  </div>
                ))}
                
                {isAiThinking && (
                  <div
                    style={{
                      padding: '12px',
                      borderRadius: '12px',
                      background: 'rgba(255, 107, 107, 0.1)',
                      borderLeft: '3px solid #ff6b6b',
                    }}
                  >
                    <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginBottom: '6px' }}>
                      🤖 FlipSide
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {[0, 1, 2].map((i) => (
                        <motion.span
                          key={i}
                          animate={{ y: [0, -5, 0] }}
                          transition={{ repeat: Infinity, duration: 0.6, delay: i * 0.15 }}
                          style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: '#ff6b6b',
                          }}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Input area */}
        <div
          style={{
            marginTop: 'auto',
            padding: '20px 24px',
            pointerEvents: 'auto',
          }}
        >
          <div
            style={{
              maxWidth: '700px',
              margin: '0 auto',
              background: 'rgba(10, 10, 20, 0.9)',
              backdropFilter: 'blur(20px)',
              borderRadius: '24px',
              border: '1px solid rgba(139, 92, 246, 0.3)',
              padding: '16px',
            }}
          >
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value.slice(0, 1200))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    handleSubmit()
                  }
                }}
                placeholder={isAiThinking ? 'FlipSide is thinking...' : 'Make your argument...'}
                disabled={isAiThinking}
                style={{
                  flex: 1,
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '16px',
                  padding: '14px 18px',
                  color: '#fff',
                  fontSize: '15px',
                  resize: 'none',
                  minHeight: '56px',
                  maxHeight: '120px',
                  outline: 'none',
                  fontFamily: 'inherit',
                }}
                rows={1}
              />
              <motion.button
                whileTap={{ scale: 0.95 }}
                whileHover={{ scale: 1.02 }}
                onClick={handleSubmit}
                disabled={!inputValue.trim() || isAiThinking}
                style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '16px',
                  border: 'none',
                  background: inputValue.trim() && !isAiThinking
                    ? 'linear-gradient(135deg, #8b5cf6, #6366f1)'
                    : 'rgba(255, 255, 255, 0.1)',
                  color: '#fff',
                  cursor: inputValue.trim() && !isAiThinking ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '20px',
                }}
              >
                {isAiThinking ? '⏳' : '🚀'}
              </motion.button>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', padding: '0 4px' }}>
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>
                {inputValue.length}/1200
              </span>
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)' }}>
                Press Ctrl+Enter to send
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SolarDebateScene
