import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Float, MeshTransmissionMaterial, MeshDistortMaterial, Sphere, Box, Torus, Icosahedron } from '@react-three/drei'
import * as THREE from 'three'

function FloatingCrystal({ position, scale = 1, color = '#8b5cf6', speed = 1 }: { 
  position: [number, number, number]
  scale?: number
  color?: string
  speed?: number
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * speed * 0.5) * 0.3
      meshRef.current.rotation.y += 0.008 * speed
    }
  })

  return (
    <Float speed={speed * 2} rotationIntensity={0.5} floatIntensity={1.5}>
      <mesh ref={meshRef} position={position} scale={scale}>
        <icosahedronGeometry args={[1, 1]} />
        <MeshTransmissionMaterial
          color={color}
          thickness={0.5}
          roughness={0.1}
          transmission={0.95}
          ior={1.5}
          chromaticAberration={0.06}
          backside
        />
      </mesh>
    </Float>
  )
}

function GlassSphere({ position, scale = 1, color = '#06b6d4' }: {
  position: [number, number, number]
  scale?: number
  color?: string
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 0.8) * 0.3
    }
  })

  return (
    <Float speed={1.5} rotationIntensity={0.3} floatIntensity={1}>
      <Sphere ref={meshRef} args={[1, 64, 64]} position={position} scale={scale}>
        <MeshTransmissionMaterial
          color={color}
          thickness={0.3}
          roughness={0}
          transmission={0.98}
          ior={1.4}
          chromaticAberration={0.03}
        />
      </Sphere>
    </Float>
  )
}

function MorphingBlob({ position, scale = 1 }: {
  position: [number, number, number]
  scale?: number
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.elapsedTime * 0.15
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.2
    }
  })

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={2}>
      <Sphere ref={meshRef} args={[1, 64, 64]} position={position} scale={scale}>
        <MeshDistortMaterial
          color="#f472b6"
          speed={2}
          distort={0.4}
          radius={1}
          transparent
          opacity={0.85}
        />
      </Sphere>
    </Float>
  )
}

function GlowingRing({ position, scale = 1, color = '#fbbf24' }: {
  position: [number, number, number]
  scale?: number
  color?: string
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.elapsedTime * 0.3
      meshRef.current.rotation.z = state.clock.elapsedTime * 0.2
    }
  })

  return (
    <Float speed={1} rotationIntensity={0.5} floatIntensity={0.8}>
      <Torus ref={meshRef} args={[1, 0.15, 32, 100]} position={position} scale={scale}>
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.5}
          metalness={0.8}
          roughness={0.2}
        />
      </Torus>
    </Float>
  )
}

function HolographicCube({ position, scale = 1 }: {
  position: [number, number, number]
  scale?: number
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  const edgesRef = useRef<THREE.LineSegments>(null)
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.elapsedTime * 0.2
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.3
    }
    if (edgesRef.current) {
      edgesRef.current.rotation.x = state.clock.elapsedTime * 0.2
      edgesRef.current.rotation.y = state.clock.elapsedTime * 0.3
    }
  })

  const edgesGeometry = useMemo(() => {
    const boxGeo = new THREE.BoxGeometry(1, 1, 1)
    return new THREE.EdgesGeometry(boxGeo)
  }, [])

  return (
    <Float speed={1.5} rotationIntensity={0.4} floatIntensity={1.2}>
      <group position={position} scale={scale}>
        <Box ref={meshRef} args={[1, 1, 1]}>
          <meshStandardMaterial
            color="#0ea5e9"
            transparent
            opacity={0.15}
            side={THREE.DoubleSide}
          />
        </Box>
        <lineSegments ref={edgesRef} geometry={edgesGeometry}>
          <lineBasicMaterial color="#38bdf8" linewidth={2} />
        </lineSegments>
      </group>
    </Float>
  )
}

function OrbitingParticles() {
  const groupRef = useRef<THREE.Group>(null)
  const particlesRef = useRef<THREE.Points>(null)
  
  const particles = useMemo(() => {
    const count = 200
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.random() * Math.PI
      const radius = 4 + Math.random() * 3
      
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = radius * Math.cos(phi)
      
      const colorChoice = Math.random()
      if (colorChoice < 0.33) {
        colors[i * 3] = 0.545
        colors[i * 3 + 1] = 0.361
        colors[i * 3 + 2] = 0.965
      } else if (colorChoice < 0.66) {
        colors[i * 3] = 0.024
        colors[i * 3 + 1] = 0.714
        colors[i * 3 + 2] = 0.831
      } else {
        colors[i * 3] = 0.957
        colors[i * 3 + 1] = 0.455
        colors[i * 3 + 2] = 0.714
      }
    }
    
    return { positions, colors }
  }, [])

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.05
      groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.1) * 0.1
    }
  })

  return (
    <group ref={groupRef}>
      <points ref={particlesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={particles.positions.length / 3}
            array={particles.positions}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-color"
            count={particles.colors.length / 3}
            array={particles.colors}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.08}
          vertexColors
          transparent
          opacity={0.8}
          sizeAttenuation
        />
      </points>
    </group>
  )
}

function NebulaField() {
  const pointsRef = useRef<THREE.Points>(null)
  
  const nebula = useMemo(() => {
    const count = 1500
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const sizes = new Float32Array(count)
    
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2
      const radius = 8 + Math.random() * 12
      const spread = (Math.random() - 0.5) * 8
      
      positions[i * 3] = Math.cos(theta) * radius + (Math.random() - 0.5) * 4
      positions[i * 3 + 1] = spread
      positions[i * 3 + 2] = Math.sin(theta) * radius + (Math.random() - 0.5) * 4
      
      const colorMix = Math.random()
      if (colorMix < 0.4) {
        colors[i * 3] = 0.4 + Math.random() * 0.2
        colors[i * 3 + 1] = 0.2 + Math.random() * 0.2
        colors[i * 3 + 2] = 0.8 + Math.random() * 0.2
      } else if (colorMix < 0.7) {
        colors[i * 3] = 0.1 + Math.random() * 0.2
        colors[i * 3 + 1] = 0.6 + Math.random() * 0.3
        colors[i * 3 + 2] = 0.8 + Math.random() * 0.2
      } else {
        colors[i * 3] = 0.9 + Math.random() * 0.1
        colors[i * 3 + 1] = 0.4 + Math.random() * 0.3
        colors[i * 3 + 2] = 0.6 + Math.random() * 0.2
      }
      
      sizes[i] = Math.random() * 0.15 + 0.03
    }
    
    return { positions, colors, sizes }
  }, [])

  useFrame((state) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y = state.clock.elapsedTime * 0.02
    }
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={nebula.positions.length / 3}
          array={nebula.positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={nebula.colors.length / 3}
          array={nebula.colors}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.12}
        vertexColors
        transparent
        opacity={0.4}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

function CentralCore() {
  const coreRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)
  
  useFrame((state) => {
    if (coreRef.current) {
      coreRef.current.rotation.y = state.clock.elapsedTime * 0.5
      const scale = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.05
      coreRef.current.scale.setScalar(scale)
    }
    if (glowRef.current) {
      const glowScale = 1.3 + Math.sin(state.clock.elapsedTime * 1.5) * 0.1
      glowRef.current.scale.setScalar(glowScale)
    }
  })

  return (
    <group>
      <Icosahedron ref={coreRef} args={[0.8, 2]} position={[0, 0, 0]}>
        <MeshTransmissionMaterial
          color="#a855f7"
          thickness={0.8}
          roughness={0}
          transmission={0.9}
          ior={2.4}
          chromaticAberration={0.1}
          backside
        />
      </Icosahedron>
      <Sphere ref={glowRef} args={[1, 32, 32]} position={[0, 0, 0]}>
        <meshStandardMaterial
          color="#c084fc"
          emissive="#a855f7"
          emissiveIntensity={0.3}
          transparent
          opacity={0.15}
        />
      </Sphere>
    </group>
  )
}

export function Scene3D() {
  return (
    <>
      <color attach="background" args={['#030712']} />
      <fog attach="fog" args={['#030712', 8, 25]} />
      
      <ambientLight intensity={0.4} />
      <directionalLight position={[10, 10, 5]} intensity={1} color="#f0f0ff" />
      <directionalLight position={[-10, -5, -10]} intensity={0.5} color="#8b5cf6" />
      <pointLight position={[0, 5, 0]} intensity={1} color="#06b6d4" distance={15} />
      <pointLight position={[0, -5, 0]} intensity={0.5} color="#f472b6" distance={10} />
      
      <CentralCore />
      <OrbitingParticles />
      <NebulaField />
      
      <FloatingCrystal position={[-3, 1.5, -1]} scale={0.6} color="#8b5cf6" speed={0.8} />
      <FloatingCrystal position={[3.5, -0.5, 1]} scale={0.45} color="#06b6d4" speed={1.2} />
      <FloatingCrystal position={[1.5, 2, -2.5]} scale={0.35} color="#f472b6" speed={1} />
      
      <GlassSphere position={[-2.5, -1, 2]} scale={0.5} color="#0ea5e9" />
      <GlassSphere position={[2, 1.8, 1.5]} scale={0.35} color="#a855f7" />
      
      <MorphingBlob position={[4, 0.5, -1.5]} scale={0.4} />
      <MorphingBlob position={[-3.5, -1.5, -2]} scale={0.3} />
      
      <GlowingRing position={[-1.5, 2.5, 0]} scale={0.5} color="#fbbf24" />
      <GlowingRing position={[2.5, -2, -1]} scale={0.4} color="#f472b6" />
      
      <HolographicCube position={[0, -2.5, 2]} scale={0.8} />
      <HolographicCube position={[-4, 0, 0]} scale={0.5} />
    </>
  )
}
