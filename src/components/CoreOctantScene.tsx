import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Edges, Html, Line, OrbitControls, Stars } from '@react-three/drei'
import * as THREE from 'three'
import type { AriaResearchRun } from '../lib/backendClient'

type Vec3 = [number, number, number]

interface CoreOctantSceneProps {
    researchRun: AriaResearchRun | null
    outputSummary: string
    guideSummary: string
    decisionLog: string
}

function trunc(text: string, max = 180): string {
    const compact = text.replace(/\s+/g, ' ').trim()
    return compact.length <= max ? compact : `${compact.slice(0, max - 1)}…`
}

function SphereCore() {
    const coreRef = useRef<THREE.Mesh | null>(null)
    const shellRef = useRef<THREE.Mesh | null>(null)
    const ringRef = useRef<THREE.Mesh | null>(null)

    useFrame(({ clock }) => {
        const t = clock.getElapsedTime()
        if (coreRef.current) {
            coreRef.current.rotation.y = t * 0.18
            coreRef.current.rotation.x = Math.sin(t * 0.18) * 0.1
            const pulse = 1 + Math.sin(t * 0.9) * 0.025
            coreRef.current.scale.setScalar(pulse)
        }
        if (shellRef.current) shellRef.current.rotation.y = -t * 0.1
        if (ringRef.current) {
            ringRef.current.rotation.y = t * 0.35
            ringRef.current.rotation.x = Math.PI * 0.5 + Math.sin(t * 0.25) * 0.12
        }
    })

    return (
        <group>
            <mesh ref={coreRef}>
                <sphereGeometry args={[1.02, 56, 56]} />
                <meshPhysicalMaterial
                    color="#8db8ff"
                    emissive="#355ca9"
                    emissiveIntensity={0.42}
                    roughness={0.14}
                    metalness={0.58}
                    clearcoat={0.95}
                />
            </mesh>

            <mesh ref={shellRef}>
                <sphereGeometry args={[1.38, 38, 38]} />
                <meshPhysicalMaterial color="#6d8dc9" transparent opacity={0.12} roughness={0.22} metalness={0.68} />
                <Edges color="#7ea8f0" threshold={25} />
            </mesh>

            <mesh ref={ringRef}>
                <torusGeometry args={[1.62, 0.03, 18, 120]} />
                <meshStandardMaterial color="#97b8ff" emissive="#3e63b0" emissiveIntensity={0.45} />
            </mesh>

            <Html transform center distanceFactor={10} position={[0, -1.8, 0]}>
                <div className="fs3d-node-label fs3d-node-label-core">ARIA Sphere</div>
            </Html>
        </group>
    )
}

function NodePoint({ position, title, body, tone = 'agent', basePosition }: { position: Vec3; title: string; body: string; tone?: 'agent' | 'output'; basePosition: Vec3 }) {
    const coreRef = useRef<THREE.Group | null>(null)
    
    useFrame(({ clock }) => {
        if (!coreRef.current) return
        const t = clock.getElapsedTime()
        
        // Radial expansion: nodes expand outward from their octants over time
        const expansionPhase = Math.max(0, Math.min(1, (t - 0.2) / 3))
        const expansion = 1 + expansionPhase * 1.2
        
        const basePosVec = new THREE.Vector3(basePosition[0], basePosition[1], basePosition[2])
        const scale = expansion
        coreRef.current.position.copy(basePosVec.multiplyScalar(scale))
        
        // Gentle rotation for ethereal effect
        coreRef.current.rotation.x += 0.002
        coreRef.current.rotation.y += 0.003
    })

    return (
        <group ref={coreRef} position={position}>
            {/* Core paraboloid mesh - liquid glass style */}
            <mesh>
                <icosahedronGeometry args={[0.32, 3]} />
                <meshPhysicalMaterial
                    color={tone === 'agent' ? '#7ba7ff' : '#6fd8c5'}
                    transparent
                    opacity={0.48}
                    roughness={0.08}
                    metalness={0.24}
                    clearcoat={0.88}
                    emissive={tone === 'agent' ? '#2d4fa0' : '#1a6c54'}
                    emissiveIntensity={0.18}
                />
                <Edges color={tone === 'agent' ? '#8fb3ff' : '#7edcc7'} threshold={20} />
            </mesh>

            {/* Inner glass shell for depth */}
            <mesh scale={0.72}>
                <icosahedronGeometry args={[0.32, 3]} />
                <meshPhysicalMaterial
                    color={tone === 'agent' ? '#a9c9ff' : '#8fe8d5'}
                    transparent
                    opacity={0.22}
                    roughness={0.06}
                    metalness={0.12}
                    clearcoat={0.92}
                />
            </mesh>

            {/* Outer glow shell */}
            <mesh scale={1.48}>
                <icosahedronGeometry args={[0.32, 2]} />
                <meshBasicMaterial
                    color={tone === 'agent' ? '#7ba7ff' : '#6fd8c5'}
                    transparent
                    opacity={0.06}
                    side={THREE.BackSide}
                />
            </mesh>

            <Html transform center distanceFactor={11} position={[0, 1.2, 0]}>
                <div className={`fs3d-node-label ${tone === 'agent' ? 'is-agent' : 'is-output'}`}>
                    <h4>{title}</h4>
                    <p>{trunc(body, tone === 'agent' ? 120 : 140)}</p>
                </div>
            </Html>
        </group>
    )
}

function OctantPlane({ rotation, color }: { rotation: Vec3; color: string }) {
    return (
        <mesh rotation={rotation}>
            <planeGeometry args={[9.2, 9.2]} />
            <meshBasicMaterial color={color} transparent opacity={0} side={THREE.DoubleSide} />
        </mesh>
    )
}

function VolumeFrame() {
    const points = useMemo(() => {
        const s = 4.6
        return [
            [-s, -s, -s],
            [s, -s, -s],
            [s, s, -s],
            [-s, s, -s],
            [-s, -s, -s],
            [-s, -s, s],
            [s, -s, s],
            [s, s, s],
            [-s, s, s],
            [-s, -s, s],
            [s, -s, s],
            [s, -s, -s],
            [s, s, -s],
            [s, s, s],
            [-s, s, s],
            [-s, s, -s],
        ] as Vec3[]
    }, [])

    return <Line points={points} color="#628ccf" lineWidth={1} transparent opacity={0.36} />
}

function Connector({ to }: { to: Vec3 }) {
    const points = useMemo(() => {
        const bend = to[1] >= 0 ? 0.55 : -0.38
        return [
            [0, 0, 0],
            [to[0] * 0.46, to[1] * 0.46 + bend, to[2] * 0.46],
            to,
        ] as Vec3[]
    }, [to])

    return <Line points={points} color="#91b6f0" lineWidth={1.2} transparent opacity={0.78} />
}

export function CoreOctantScene({ researchRun, outputSummary, guideSummary, decisionLog }: CoreOctantSceneProps) {
    const basePositions = useMemo(() => ({
        advocate: [-2.8, 2.2, -2.2] as Vec3,
        skeptic: [-2.8, 2.2, 2.2] as Vec3,
        domain: [2.8, 2.2, -2.2] as Vec3,
        arbitrator: [2.8, 2.2, 2.2] as Vec3,
        output: [-2.5, -2.25, -2.35] as Vec3,
        guide: [2.5, -2.25, -2.35] as Vec3,
        decision: [0, -2.3, 2.55] as Vec3,
    }), [])

    const nodes = useMemo(() => {
        const advocate = researchRun?.agents.advocate.summary || 'Support-side agent summary will appear here.'
        const skeptic = researchRun?.agents.skeptic.summary || 'Challenge-side agent summary will appear here.'
        const domain = researchRun?.agents.domain.summary || 'Domain constraints and standards summary will appear here.'
        const arbitrator = researchRun?.agents.arbitrator.summary || 'Final arbitration summary will appear here.'

        return [
            { key: 'advocate', title: 'Advocate', body: advocate, position: basePositions.advocate, basePosition: basePositions.advocate, tone: 'agent' as const },
            { key: 'skeptic', title: 'Skeptic', body: skeptic, position: basePositions.skeptic, basePosition: basePositions.skeptic, tone: 'agent' as const },
            { key: 'domain', title: 'Domain', body: domain, position: basePositions.domain, basePosition: basePositions.domain, tone: 'agent' as const },
            { key: 'arbitrator', title: 'Arbitrator', body: arbitrator, position: basePositions.arbitrator, basePosition: basePositions.arbitrator, tone: 'agent' as const },
            { key: 'output', title: 'Primary Output', body: outputSummary, position: basePositions.output, basePosition: basePositions.output, tone: 'output' as const },
            { key: 'guide', title: 'Guide Agent', body: guideSummary, position: basePositions.guide, basePosition: basePositions.guide, tone: 'output' as const },
            { key: 'decision', title: 'Decision + Change Log', body: decisionLog, position: basePositions.decision, basePosition: basePositions.decision, tone: 'output' as const },
        ]
    }, [researchRun, outputSummary, guideSummary, decisionLog, basePositions])

    return (
        <div className="fs3d-core-scene-wrap" aria-label="3D octant processing scene">
            <Canvas camera={{ position: [0, 1.9, 10.8], fov: 46 }}>
                <color attach="background" args={['#03070f']} />
                <fog attach="fog" args={['#03070f', 10, 22]} />

                <ambientLight intensity={0.28} />
                <hemisphereLight intensity={0.3} color="#bfd6ff" groundColor="#041326" />
                <directionalLight position={[4, 6, 5]} intensity={1.4} color="#a9c6ff" />
                <pointLight position={[0, 2.2, 2]} intensity={2.6} color="#7ca7ff" distance={15} />
                <pointLight position={[0, -2.8, -2]} intensity={1.4} color="#66d8bf" distance={14} />

                <Stars radius={34} depth={45} count={700} factor={2.2} saturation={0.2} fade speed={0.25} />

                <VolumeFrame />

                <OctantPlane rotation={[0, 0, 0]} color="#6b8dc9" />
                <OctantPlane rotation={[Math.PI / 2, 0, 0]} color="#6b8dc9" />
                <OctantPlane rotation={[0, Math.PI / 2, 0]} color="#6b8dc9" />

                <Line points={[[-4.7, 0, 0], [4.7, 0, 0]]} color="#7ea4df" transparent opacity={0.55} />
                <Line points={[[0, -4.7, 0], [0, 4.7, 0]]} color="#7ea4df" transparent opacity={0.55} />
                <Line points={[[0, 0, -4.7], [0, 0, 4.7]]} color="#7ea4df" transparent opacity={0.55} />

                <SphereCore />

                {nodes.map((node) => (
                    <group key={node.key}>
                        <Connector to={node.position} />
                        <NodePoint position={node.position} title={node.title} body={node.body} tone={node.tone} basePosition={node.basePosition} />
                    </group>
                ))}

                <OrbitControls
                    enablePan={false}
                    enableDamping
                    dampingFactor={0.05}
                    rotateSpeed={0.6}
                    maxDistance={24}
                    minDistance={6.5}
                    minPolarAngle={0.5}
                    maxPolarAngle={2.2}
                />
            </Canvas>
        </div>
    )
}
