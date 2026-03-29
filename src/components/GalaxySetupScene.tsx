import { useMemo, useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Billboard, Html, OrbitControls, Sparkles, Stars } from '@react-three/drei'
import { motion } from 'framer-motion'
import * as THREE from 'three'

type ResearchDepth = 'quick' | 'standard' | 'deep'

type Vec3 = [number, number, number]
type Vec4 = [number, number, number, number]

interface GalaxySetupProps {
    onSelectTopic: (topic: string) => void
    onStartResearch: (config: { topic: string; depth: ResearchDepth; maxSources: number }) => void
    onStartDecisionGraph: () => void
    presetTopics?: string[]
}

function buildHexagonVertices(radius: number): Vec3[] {
    return Array.from({ length: 6 }, (_, i) => {
        const angle = (i / 6) * Math.PI * 2
        return [Math.cos(angle) * radius, Math.sin(angle) * radius, 0]
    })
}

function generateTesseract(size: number) {
    const half = size / 2
    const vertices: Vec4[] = []

    for (let i = 0; i < 16; i += 1) {
        const x = (i & 1) ? half : -half
        const y = (i & 2) ? half : -half
        const z = (i & 4) ? half : -half
        const w = (i & 8) ? half : -half
        vertices.push([x, y, z, w])
    }

    const edges: Array<[number, number]> = []
    for (let a = 0; a < 16; a += 1) {
        for (let bit = 0; bit < 4; bit += 1) {
            const b = a ^ (1 << bit)
            if (a < b) edges.push([a, b])
        }
    }

    return { vertices, edges }
}

function project4DTo3D(vertex4D: Vec4, distance: number): Vec3 {
    const denom = distance - vertex4D[3]
    const safeDenom = Math.abs(denom) < 1e-4 ? (denom < 0 ? -1e-4 : 1e-4) : denom
    const wFactor = 1 / safeDenom

    return [vertex4D[0] * wFactor, vertex4D[1] * wFactor, vertex4D[2] * wFactor]
}

function projectTesseractVerticesAtTime(
    vertices: Vec4[],
    projectionDistance: number,
    scale: number,
    t: number,
): Vec3[] {
    const tScaled = t * 1.5
    const angleXW = 0.52 + Math.sin(tScaled * 0.32) * 0.17
    const angleYW = -0.38 + Math.cos(tScaled * 0.25) * 0.14
    const angleZW = 0.26 + Math.sin(tScaled * 0.21) * 0.12
    const cXW = Math.cos(angleXW)
    const sXW = Math.sin(angleXW)
    const cYW = Math.cos(angleYW)
    const sYW = Math.sin(angleYW)
    const cZW = Math.cos(angleZW)
    const sZW = Math.sin(angleZW)

    return vertices.map(([x0, y0, z0, w0]) => {
        const x1 = x0 * cXW - w0 * sXW
        const w1 = x0 * sXW + w0 * cXW

        const y2 = y0 * cYW - w1 * sYW
        const w2 = y0 * sYW + w1 * cYW

        const z3 = z0 * cZW - w2 * sZW
        const w3 = z0 * sZW + w2 * cZW

        const p = project4DTo3D([x1, y2, z3, w3], projectionDistance)
        return [p[0] * scale, p[1] * scale, p[2] * scale] as Vec3
    })
}

function Tesseract4DSystem({
    size,
    projectionDistance,
    scale,
    agentCenters,
    color = '#8ea8ff',
}: {
    size: number
    projectionDistance: number
    scale: number
    agentCenters: { advocate: Vec3; skeptic: Vec3; domain: Vec3; arbitrator: Vec3 }
    color?: string
}) {
    const structure = useMemo(() => generateTesseract(size), [size])

    const initialProjected = useMemo(
        () => projectTesseractVerticesAtTime(structure.vertices, projectionDistance, scale, 0),
        [structure.vertices, projectionDistance, scale],
    )

    const agentVertexMap = useMemo(() => {
        const used = new Set<number>()
        const pickNearestUnused = (target: Vec3) => {
            let bestIndex = 0
            let bestDist = Number.POSITIVE_INFINITY
            for (let i = 0; i < initialProjected.length; i += 1) {
                if (used.has(i)) continue
                const p = initialProjected[i]
                const dx = p[0] - target[0]
                const dy = p[1] - target[1]
                const dz = p[2] - target[2]
                const dist = dx * dx + dy * dy + dz * dz
                if (dist < bestDist) {
                    bestDist = dist
                    bestIndex = i
                }
            }
            used.add(bestIndex)
            return bestIndex
        }

        return {
            advocate: pickNearestUnused(agentCenters.advocate),
            skeptic: pickNearestUnused(agentCenters.skeptic),
            domain: pickNearestUnused(agentCenters.domain),
            arbitrator: pickNearestUnused(agentCenters.arbitrator),
        }
    }, [initialProjected, agentCenters])

    const wireAttrRef = useRef<THREE.BufferAttribute | null>(null)
    const nodeAttrRef = useRef<THREE.BufferAttribute | null>(null)
    const agentLinkAttrRef = useRef<THREE.BufferAttribute | null>(null)

    const wirePositions = useMemo(() => new Float32Array(structure.edges.length * 2 * 3), [structure.edges.length])
    const nodePositions = useMemo(() => new Float32Array(structure.vertices.length * 3), [structure.vertices.length])
    const agentLinkPositions = useMemo(() => new Float32Array(4 * 2 * 3), [])

    useFrame((state) => {
        const wireAttr = wireAttrRef.current
        const nodeAttr = nodeAttrRef.current
        const agentAttr = agentLinkAttrRef.current
        if (!wireAttr || !nodeAttr || !agentAttr) return

        const projected = projectTesseractVerticesAtTime(structure.vertices, projectionDistance, scale, state.clock.getElapsedTime())

        const wireArray = wireAttr.array as Float32Array
        const nodeArray = nodeAttr.array as Float32Array
        const agentArray = agentAttr.array as Float32Array

        for (let i = 0; i < projected.length; i += 1) {
            const idx = i * 3
            nodeArray[idx] = projected[i][0]
            nodeArray[idx + 1] = projected[i][1]
            nodeArray[idx + 2] = projected[i][2]
        }

        for (let i = 0; i < structure.edges.length; i += 1) {
            const [a, b] = structure.edges[i]
            const base = i * 6
            wireArray[base] = projected[a][0]
            wireArray[base + 1] = projected[a][1]
            wireArray[base + 2] = projected[a][2]
            wireArray[base + 3] = projected[b][0]
            wireArray[base + 4] = projected[b][1]
            wireArray[base + 5] = projected[b][2]
        }

        const agents: Array<{ center: Vec3; vertexIndex: number }> = [
            { center: agentCenters.advocate, vertexIndex: agentVertexMap.advocate },
            { center: agentCenters.skeptic, vertexIndex: agentVertexMap.skeptic },
            { center: agentCenters.domain, vertexIndex: agentVertexMap.domain },
            { center: agentCenters.arbitrator, vertexIndex: agentVertexMap.arbitrator },
        ]

        agents.forEach((agent, i) => {
            const base = i * 6
            const target = projected[agent.vertexIndex]
            agentArray[base] = agent.center[0]
            agentArray[base + 1] = agent.center[1]
            agentArray[base + 2] = agent.center[2]
            agentArray[base + 3] = target[0]
            agentArray[base + 4] = target[1]
            agentArray[base + 5] = target[2]
        })

        wireAttr.needsUpdate = true
        nodeAttr.needsUpdate = true
        agentAttr.needsUpdate = true
    })

    return (
        <group>
            <lineSegments>
                <bufferGeometry>
                    <bufferAttribute ref={wireAttrRef} attach="attributes-position" args={[wirePositions, 3]} />
                </bufferGeometry>
                <lineBasicMaterial color={color} linewidth={2} transparent opacity={0.82} />
            </lineSegments>

            <points>
                <bufferGeometry>
                    <bufferAttribute ref={nodeAttrRef} attach="attributes-position" args={[nodePositions, 3]} />
                </bufferGeometry>
                <pointsMaterial color="#d9e6ff" size={0.26} sizeAttenuation transparent opacity={0.95} />
            </points>

            <lineSegments>
                <bufferGeometry>
                    <bufferAttribute ref={agentLinkAttrRef} attach="attributes-position" args={[agentLinkPositions, 3]} />
                </bufferGeometry>
                <lineBasicMaterial color="#9fd3ff" transparent opacity={0.9} />
            </lineSegments>
        </group>
    )
}

function ConnectionLine({ from, to, color = '#9cc9ff' }: { from: Vec3; to: Vec3; color?: string }) {
    const positions = useMemo(() => new Float32Array([from[0], from[1], from[2], to[0], to[1], to[2]]), [from, to])

    return (
        <lineSegments>
            <bufferGeometry>
                <bufferAttribute attach="attributes-position" args={[positions, 3]} />
            </bufferGeometry>
            <lineBasicMaterial color={color} transparent opacity={0.85} />
        </lineSegments>
    )
}

function SinWaveConnector({
    from,
    to,
    color,
    amplitude = 0.55,
    speed = 2,
    waveCount = 5,
}: {
    from: Vec3
    to: Vec3
    color: string
    amplitude?: number
    speed?: number
    waveCount?: number
}) {
    const geometryRef = useRef<THREE.BufferGeometry | null>(null)
    const segments = 72

    const baseData = useMemo(() => {
        const start = new THREE.Vector3(...from)
        const end = new THREE.Vector3(...to)
        const dir = end.clone().sub(start)
        const dirXY = new THREE.Vector2(dir.x, dir.y).normalize()
        const normal = new THREE.Vector2(-dirXY.y, dirXY.x)
        return { start, end, normal }
    }, [from, to])

    useFrame((state) => {
        const geometry = geometryRef.current
        if (!geometry) return
        const pos = geometry.attributes.position.array as Float32Array
        const tNow = state.clock.getElapsedTime()

        for (let i = 0; i < segments; i += 1) {
            const t = i / (segments - 1)
            const x = THREE.MathUtils.lerp(baseData.start.x, baseData.end.x, t)
            const y = THREE.MathUtils.lerp(baseData.start.y, baseData.end.y, t)
            const z = THREE.MathUtils.lerp(baseData.start.z, baseData.end.z, t)

            const taper = Math.sin(Math.PI * t)
            const offset = Math.sin(t * waveCount * Math.PI * 2 + tNow * speed) * amplitude * taper

            const idx = i * 3
            pos[idx] = x + baseData.normal.x * offset
            pos[idx + 1] = y + baseData.normal.y * offset
            pos[idx + 2] = z
        }

        geometry.attributes.position.needsUpdate = true
    })

    return (
        <line>
            <bufferGeometry ref={geometryRef}>
                <bufferAttribute attach="attributes-position" args={[new Float32Array(segments * 3), 3]} />
            </bufferGeometry>
            <lineBasicMaterial color={color} transparent opacity={0.92} />
        </line>
    )
}

function AgentRing({ center, radius, color, label, spin = 1 }: { center: Vec3; radius: number; color: string; label: string; spin?: number }) {
    const groupRef = useRef<THREE.Group | null>(null)
    const lineCount = 40
    const segments = 128
    const lineAttrRefs = useRef<Array<THREE.BufferAttribute | null>>([])

    const gradientStops = useMemo(() => [
        new THREE.Color('#3aa7ff'),
        new THREE.Color('#8b5cf6'),
        new THREE.Color('#ff9a3d'),
    ], [])

    const lineColors = useMemo(() => {
        const colors: string[] = []
        for (let i = 0; i < lineCount; i += 1) {
            const t = i / Math.max(1, lineCount - 1)
            const c = new THREE.Color()
            if (t < 0.5) {
                c.copy(gradientStops[0]).lerp(gradientStops[1], t / 0.5)
            } else {
                c.copy(gradientStops[1]).lerp(gradientStops[2], (t - 0.5) / 0.5)
            }
            colors.push(`#${c.getHexString()}`)
        }
        return colors
    }, [gradientStops])

    const basePositions = useMemo(() => {
        return Array.from({ length: lineCount }, () => new Float32Array(segments * 3))
    }, [lineCount])

    useFrame((_, delta) => {
        if (!groupRef.current) return

        const tNow = performance.now() * 0.001
        const freq = 5.2
        const amp = radius * 0.08

        for (let lineIdx = 0; lineIdx < lineCount; lineIdx += 1) {
            const attr = lineAttrRefs.current[lineIdx]
            if (!attr) continue
            const arr = attr.array as Float32Array
            const phase = tNow * 1.6 + lineIdx * 0.22
            const zOffset = (lineIdx - lineCount / 2) * 0.008

            for (let j = 0; j < segments; j += 1) {
                const theta = (j / segments) * Math.PI * 2
                const r = radius + Math.sin(theta * freq + phase) * amp
                const idx = j * 3
                arr[idx] = Math.cos(theta) * r
                arr[idx + 1] = Math.sin(theta) * r
                arr[idx + 2] = zOffset
            }

            attr.needsUpdate = true
        }

        groupRef.current.rotation.z += delta * 0.2 * spin
    })

    return (
        <group ref={groupRef} position={center}>
            {basePositions.map((line, idx) => (
                <lineLoop key={`${label}-ribbon-${idx}`}>
                    <bufferGeometry>
                        <bufferAttribute
                            ref={(el) => {
                                lineAttrRefs.current[idx] = el
                            }}
                            attach="attributes-position"
                            args={[line, 3]}
                        />
                    </bufferGeometry>
                    <lineBasicMaterial color={lineColors[idx]} transparent opacity={0.36} />
                </lineLoop>
            ))}
            <mesh>
                <sphereGeometry args={[0.14, 14, 14]} />
                <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.48} />
            </mesh>
            <Html transform sprite distanceFactor={13} position={[0, 0, 0.15]}>
                <div className="fs3d-agent-ring-label">{label}</div>
            </Html>
        </group>
    )
}

function DiamondTask({ position, label, color, disabled }: { position: Vec3; label: string; color: string; disabled: boolean }) {
    return (
        <Billboard follow position={position}>
            <mesh>
                <octahedronGeometry args={[0.5, 0]} />
                <meshPhysicalMaterial
                    color={disabled ? '#56657f' : color}
                    emissive={disabled ? '#2a3346' : color}
                    emissiveIntensity={disabled ? 0.18 : 0.34}
                    roughness={0.18}
                    metalness={0.46}
                />
            </mesh>
            <Html transform sprite position={[0, 0.8, 0.1]} distanceFactor={12}>
                <div className={`fs3d-task-diamond-label ${disabled ? 'is-disabled' : ''}`}>{label}</div>
            </Html>
        </Billboard>
    )
}

function OutputCuboid({ position }: { position: Vec3 }) {
    return (
        <group position={position}>
            <mesh>
                <boxGeometry args={[4.4, 1.05, 0.64]} />
                <meshPhysicalMaterial color="#56dbff" emissive="#2ca9d6" emissiveIntensity={0.35} roughness={0.28} metalness={0.42} />
            </mesh>
            <Html transform sprite position={[0, 0, 0.34]} distanceFactor={11}>
                <div className="fs3d-research-output-box">Output</div>
            </Html>
        </group>
    )
}

function AgentResearchVolume({
    origin,
    color,
    title,
    phase,
    statements,
}: {
    origin: Vec3
    color: string
    title: string
    phase: number
    statements: Array<{ text: string; source: string }>
}) {
    const groupRef = useRef<THREE.Group | null>(null)
    const nodes = useMemo(() => {
        const list: Array<{ id: string; p: Vec3; text: string; source: string }> = []
        list.push({ id: `${title}-root`, p: [0, 0, -0.8], text: `${title} stream`, source: 'internal synthesis' })

        const layer1 = statements.slice(0, 3)
        layer1.forEach((item, i) => {
            const theta = -0.8 + i * 0.8
            const r = 3.1
            const z = -1.2 - 0.32 * r * r
            list.push({
                id: `${title}-l1-${i}`,
                p: [Math.cos(theta) * r, Math.sin(theta) * r - 0.7, z],
                text: item.text,
                source: item.source,
            })
        })

        layer1.forEach((item, i) => {
            const theta = -0.95 + i * 0.95
            const r = 5.2
            const z = -1.2 - 0.26 * r * r
            list.push({
                id: `${title}-l2-${i}`,
                p: [Math.cos(theta) * r, Math.sin(theta) * r - 1.5, z],
                text: `detail: ${item.text.slice(0, 34)}...`,
                source: item.source,
            })
        })

        return list
    }, [statements, title])

    const edges = useMemo(() => {
        const map = new Map(nodes.map((n) => [n.id, n]))
        const root = `${title}-root`
        const list: Array<[Vec3, Vec3]> = []
        for (let i = 0; i < 3; i += 1) {
            const l1 = map.get(`${title}-l1-${i}`)
            const l2 = map.get(`${title}-l2-${i}`)
            const rootNode = map.get(root)
            if (rootNode && l1) list.push([rootNode.p, l1.p])
            if (l1 && l2) list.push([l1.p, l2.p])
        }
        return list
    }, [nodes, title])

    useFrame((state) => {
        if (!groupRef.current) return
        const t = state.clock.getElapsedTime()
        groupRef.current.position.set(
            origin[0] + Math.sin(t * 0.72 + phase) * 0.32,
            origin[1] + Math.sin(t * 1.15 + phase * 1.4) * 0.45,
            origin[2] + Math.cos(t * 0.8 + phase) * 0.55,
        )
    })

    return (
        <group ref={groupRef} position={origin}>
            {edges.map((pair, idx) => (
                <ConnectionLine key={`${title}-edge-${idx}`} from={pair[0]} to={pair[1]} color={color} />
            ))}

            {nodes.map((node, idx) => (
                <Billboard key={node.id} follow position={node.p}>
                    <mesh>
                        <sphereGeometry args={[idx === 0 ? 0.22 : 0.15, 14, 14]} />
                        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={idx === 0 ? 0.45 : 0.28} />
                    </mesh>
                    <Html transform sprite distanceFactor={13} position={[0, 0.45, 0.05]}>
                        <div className="fs3d-research-node-label">
                            <div>{node.text}</div>
                            <div className="fs3d-research-node-source">source: {node.source}</div>
                        </div>
                    </Html>
                </Billboard>
            ))}
        </group>
    )
}

export function GalaxySetupScene({ onSelectTopic, onStartResearch }: GalaxySetupProps) {
    const [userInput, setUserInput] = useState('')
    const [depth, setDepth] = useState<ResearchDepth>('standard')
    const [maxSources, setMaxSources] = useState(6)
    const [wordLength, setWordLength] = useState(900)
    const [tone, setTone] = useState('balanced')
    const [desiredOutputType, setDesiredOutputType] = useState('report')
    const [isResearchReady, setIsResearchReady] = useState(false)
    const [isPrimarySaved, setIsPrimarySaved] = useState(false)
    const [guideQuestion, setGuideQuestion] = useState('')
    const [primaryOutput, setPrimaryOutput] = useState('')
    const [decisionLog, setDecisionLog] = useState<string[]>([
        'System initialized in local mode.',
        'Awaiting research topic input.',
    ])

    const hexVertices = useMemo(() => buildHexagonVertices(10), [])

    const outputVertex = hexVertices[0]

    const outputBoxCenter = useMemo<Vec3>(() => [outputVertex[0] + 5.2, outputVertex[1], outputVertex[2]], [outputVertex])

    const outputConnectionPoint = useMemo<Vec3>(() => [outputBoxCenter[0] - 2.2, outputBoxCenter[1], outputBoxCenter[2]], [outputBoxCenter])
    const windowOneCenter = useMemo<Vec3>(() => [-26, 8.5, 0], [])
    const windowTwoCenter = useMemo<Vec3>(() => [0, 8.5, 0], [])
    const windowThreeCenter = useMemo<Vec3>(() => [26, 8.5, 0], [])

    const edgeData = useMemo(() => {
        const connectorLength = 3.6
        const buildAgentAnchor = (vertexIndex: number) => {
            const vertex = hexVertices[vertexIndex]
            const vertexVec = new THREE.Vector3(...vertex)
            const outward = vertexVec.clone().normalize()
            return {
                vertex,
                center: [
                    vertexVec.x + outward.x * connectorLength,
                    vertexVec.y + outward.y * connectorLength,
                    vertexVec.z,
                ] as Vec3,
            }
        }

        return {
            advocate: buildAgentAnchor(2),
            skeptic: buildAgentAnchor(1),
            domain: buildAgentAnchor(4),
            arbitrator: buildAgentAnchor(5),
        }
    }, [hexVertices])

    const primaryNodePosition = useMemo<Vec3>(() => [outputBoxCenter[0], outputBoxCenter[1] - 8.6, -0.5], [outputBoxCenter])
    const sideNodePosition = useMemo<Vec3>(() => [primaryNodePosition[0] + 8.4, primaryNodePosition[1] - 2.6, 0.2], [primaryNodePosition])
    const guideAgentCenter = useMemo<Vec3>(() => [primaryNodePosition[0] - 10.8, primaryNodePosition[1] + 0.9, 0.2], [primaryNodePosition])

    const liveResearchOrigins = useMemo(() => ({
        advocate: [edgeData.advocate.center[0], edgeData.advocate.center[1], -8.8] as Vec3,
        skeptic: [edgeData.skeptic.center[0], edgeData.skeptic.center[1], -8.8] as Vec3,
        domain: [edgeData.domain.center[0], edgeData.domain.center[1], -8.8] as Vec3,
        arbitrator: [edgeData.arbitrator.center[0], edgeData.arbitrator.center[1], -8.8] as Vec3,
    }), [edgeData])

    const liveStreams = useMemo(() => {
        const topic = userInput.trim() || 'current research topic'
        return {
            advocate: [
                { text: `benefit: ${topic} improves speed for new coders`, source: 'developer survey meta' },
                { text: 'proposal: scaffolded copiloting reduces setup friction', source: 'edtech benchmark 2025' },
                { text: 'efficiency gains in repetitive coding tasks', source: 'industry productivity report' },
            ],
            skeptic: [
                { text: `denial: ${topic} may weaken first-principles learning`, source: 'learning outcomes review' },
                { text: 'conflict: over-reliance increases debugging blind spots', source: 'software quality audit' },
                { text: 'proposal rejected without verification loop', source: 'safety practice note' },
            ],
            domain: [
                { text: 'baseline: guided practice plus AI beats unguided AI', source: 'cs pedagogy study' },
                { text: 'subtopic: rubric-driven prompting required', source: 'instruction design paper' },
                { text: 'evidence tiering by source credibility', source: 'research methods handbook' },
            ],
            arbitrator: [
                { text: 'decision: adopt with constraints and milestones', source: 'arbitration policy matrix' },
                { text: 'conflict map: speed vs conceptual depth', source: 'cross-agent synthesis' },
                { text: 'change request: add verification checkpoints', source: 'final confidence pass' },
            ],
        }
    }, [userInput])

    const butterflyTasks = useMemo(() => {
        const outwardX = 11.2
        const yLevels = [7.6, 4.4, 1.2, -1.2, -4.4, -7.6]
        const labels = ['Make PDF', 'Make PPT', 'Draw Diagrams', 'Web App + Host', 'Lesson Plan', 'Citation Pack']
        const colors = ['#ff9bcf', '#ffd978', '#9bffcc', '#9dc4ff', '#ffaf93', '#d2b5ff']

        return labels.map((label, i) => ({
            label,
            position: [outputBoxCenter[0] + outwardX, outputBoxCenter[1] + yLevels[i], 0] as Vec3,
            color: colors[i],
        }))
    }, [outputBoxCenter])

    const handleInputChange = (value: string) => {
        setUserInput(value)
        onSelectTopic(value)
    }

    const handleRunResearch = () => {
        const topic = userInput.trim()
        if (!topic) return

        onStartResearch({ topic, depth, maxSources })

        const initialOutput = [
            `Topic: ${topic}`,
            `Tone: ${tone}`,
            `Target Length: ${wordLength} words`,
            `Desired Type: ${desiredOutputType}`,
            '',
            'Primary Sections:',
            '1. Executive Summary',
            '2. Key Claims and Evidence',
            '3. Counterpoints and Risks',
            '4. Domain Context',
            '5. Actionable Next Steps',
            '',
            'Subtopics:',
            '- Background and context',
            '- Supporting evidence',
            '- Contradictions and trade-offs',
            '- Knowledge gaps',
            '- Practical implementation path',
        ].join('\n')

        setPrimaryOutput(initialOutput)
        setIsResearchReady(true)
        setIsPrimarySaved(false)
        setDecisionLog((prev) => [
            `Research run started for "${topic}".`,
            'Advocate/Skeptic/Domain/Arbitrator summaries assembled in local mode.',
            ...prev,
        ])
    }

    const handleSavePrimary = () => {
        setIsPrimarySaved(true)
        setDecisionLog((prev) => ['Primary output saved and unlocked for export diamonds.', ...prev])
    }

    const handleGuideAssist = () => {
        const q = guideQuestion.trim()
        if (!q) return

        const suggested = `\n\nGuide Agent Update:\n- User question: ${q}\n- Suggested refinement: clarify assumptions, add one measurable KPI, and tighten conclusion.`
        setPrimaryOutput((prev) => prev + suggested)
        setDecisionLog((prev) => [`Guide agent applied revision for question: "${q}"`, ...prev])
        setGuideQuestion('')
    }

    return (
        <div className="fs3d-galaxy-root">
            <Canvas
                camera={{ position: [0, 0, 38], fov: 44 }}
                dpr={[1, 1.2]}
                gl={{ antialias: true, alpha: false, stencil: false, depth: true, powerPreference: 'high-performance' }}
            >
                <OrbitControls enablePan={false} minDistance={12} maxDistance={78} enableDamping dampingFactor={0.08} />
                <color attach="background" args={['#02030a']} />
                <fog attach="fog" args={['#02030a', 32, 180]} />
                <ambientLight intensity={0.36} />
                <pointLight position={[8, 9, 9]} intensity={0.7} color="#8eb7ff" />
                <pointLight position={[-9, -6, 8]} intensity={0.44} color="#49d6ff" />
                <Stars radius={240} depth={95} count={3000} factor={4} fade speed={0.3} saturation={0} />
                <Sparkles count={62} size={1} speed={0.07} scale={[62, 22, 62]} color="#98c6ff" />

                <SinWaveConnector from={windowOneCenter} to={windowThreeCenter} color="#ff3b45" amplitude={1.05} speed={1.15} waveCount={9} />

                <group position={windowOneCenter}>
                    <mesh>
                        <boxGeometry args={[14, 8.6, 0.28]} />
                        <meshPhysicalMaterial color="#7ea1ff" emissive="#5068bf" emissiveIntensity={0.26} roughness={0.2} metalness={0.35} transparent opacity={0.35} />
                    </mesh>
                    <Html transform position={[0, 0, 0.2]} distanceFactor={11}>
                        <div className="fs3d-preferences-panel fs3d-window-one-panel">
                            <div className="fs3d-preferences-title">Window 1: Input + Specs</div>
                            <input
                                value={userInput}
                                onChange={(event) => handleInputChange(event.target.value)}
                                placeholder="Type research topic..."
                                className="fs3d-research-input"
                            />
                            <label>Word Length</label>
                            <input
                                type="number"
                                title="Preferred word length"
                                aria-label="Preferred word length"
                                min={200}
                                max={5000}
                                value={wordLength}
                                onChange={(e) => setWordLength(Math.max(200, Math.min(5000, Number(e.target.value) || 900)))}
                            />
                            <label>Tone</label>
                            <select title="Preferred tone" aria-label="Preferred tone" value={tone} onChange={(e) => setTone(e.target.value)}>
                                <option value="balanced">Balanced</option>
                                <option value="academic">Academic</option>
                                <option value="concise">Concise</option>
                            </select>
                            <label>Output Type</label>
                            <select title="Desired output type" aria-label="Desired output type" value={desiredOutputType} onChange={(e) => setDesiredOutputType(e.target.value)}>
                                <option value="report">Report</option>
                                <option value="brief">Brief</option>
                                <option value="lesson">Lesson Plan</option>
                            </select>
                            <div className="fs3d-research-controls fs3d-window-one-controls">
                                <select
                                    className="fs3d-research-select"
                                    title="Research depth"
                                    aria-label="Research depth"
                                    value={depth}
                                    onChange={(event) => setDepth(event.target.value as ResearchDepth)}
                                >
                                    <option value="quick">Quick</option>
                                    <option value="standard">Standard</option>
                                    <option value="deep">Deep</option>
                                </select>
                                <select
                                    className="fs3d-research-select"
                                    title="Source breadth"
                                    aria-label="Source breadth"
                                    value={maxSources}
                                    onChange={(event) => setMaxSources(Number(event.target.value))}
                                >
                                    <option value={4}>4 sources</option>
                                    <option value={6}>6 sources</option>
                                    <option value={8}>8 sources</option>
                                </select>
                            </div>
                            <button onClick={handleRunResearch} className="fs3d-galaxy-mode-btn">Start Research</button>
                        </div>
                    </Html>
                </group>

                <group position={windowTwoCenter}>
                    <mesh>
                        <boxGeometry args={[36, 24, 0.18]} />
                        <meshPhysicalMaterial color="#8ea8ff" emissive="#5b75cc" emissiveIntensity={0.14} roughness={0.25} metalness={0.3} transparent opacity={0.14} />
                    </mesh>
                    <Html transform sprite position={[0, 12.8, 0.3]} distanceFactor={14}>
                        <div className="fs3d-agent-ring-label">Window 2: Tesseract + Output + Post-Research</div>
                    </Html>
                </group>

                <group position={windowThreeCenter}>
                    <mesh>
                        <boxGeometry args={[12, 8, 0.24]} />
                        <meshPhysicalMaterial color="#ff8aa3" emissive="#d75e7d" emissiveIntensity={0.2} roughness={0.22} metalness={0.28} transparent opacity={0.25} />
                    </mesh>
                    <Html transform position={[0, 0, 0.2]} distanceFactor={11}>
                        <div className="fs3d-preferences-panel fs3d-window-three-panel">
                            <div className="fs3d-preferences-title">Window 3</div>
                            <div>Reserved. Connected to same main wave.</div>
                        </div>
                    </Html>
                </group>

                <Tesseract4DSystem
                    size={8}
                    projectionDistance={12}
                    scale={12}
                    color="#8ea8ff"
                    agentCenters={{
                        advocate: edgeData.advocate.center,
                        skeptic: edgeData.skeptic.center,
                        domain: edgeData.domain.center,
                        arbitrator: edgeData.arbitrator.center,
                    }}
                />

                <SinWaveConnector from={outputConnectionPoint} to={outputVertex} color="#7effd2" amplitude={0.62} speed={2.3} />

                <OutputCuboid position={outputBoxCenter} />

                {butterflyTasks.map((task) => (
                    <group key={task.label}>
                        <ConnectionLine from={outputBoxCenter} to={task.position} color={isPrimarySaved ? task.color : '#4f5d7a'} />
                        <DiamondTask position={task.position} label={task.label} color={task.color} disabled={!isPrimarySaved} />
                    </group>
                ))}

                <AgentRing center={edgeData.advocate.center} radius={1.45} color="#ff7bc9" label="Advocate" spin={1} />
                <AgentRing center={edgeData.skeptic.center} radius={1.45} color="#ffd46f" label="Skeptic" spin={-1} />
                <AgentRing center={edgeData.domain.center} radius={1.45} color="#7dffac" label="Domain" spin={1} />
                <AgentRing center={edgeData.arbitrator.center} radius={1.45} color="#7cc0ff" label="Arbitrator" spin={-1} />

                {isResearchReady ? (
                    <>
                        <AgentResearchVolume origin={liveResearchOrigins.advocate} color="#ff7bc9" title="Advocate" phase={0.2} statements={liveStreams.advocate} />
                        <AgentResearchVolume origin={liveResearchOrigins.skeptic} color="#ffd46f" title="Skeptic" phase={1.1} statements={liveStreams.skeptic} />
                        <AgentResearchVolume origin={liveResearchOrigins.domain} color="#7dffac" title="Domain" phase={2.2} statements={liveStreams.domain} />
                        <AgentResearchVolume origin={liveResearchOrigins.arbitrator} color="#7cc0ff" title="Arbitrator" phase={3.1} statements={liveStreams.arbitrator} />

                        <ConnectionLine from={outputBoxCenter} to={primaryNodePosition} color="#7ef9f1" />
                        <mesh position={primaryNodePosition}>
                            <sphereGeometry args={[0.24, 14, 14]} />
                            <meshStandardMaterial color="#7ef9f1" emissive="#40c7bc" emissiveIntensity={0.42} />
                        </mesh>

                        <Html transform sprite position={[primaryNodePosition[0], primaryNodePosition[1] - 0.3, 0.2]} distanceFactor={12}>
                            <div className="fs3d-primary-output-page liquid-glass-report">
                                <div className="fs3d-primary-output-header">Primary Output (Editable)</div>
                                <textarea
                                    title="Primary output editor"
                                    aria-label="Primary output editor"
                                    placeholder="Primary output will appear here"
                                    value={primaryOutput}
                                    onChange={(e) => setPrimaryOutput(e.target.value)}
                                    className="fs3d-primary-output-text"
                                />
                                <button onClick={handleSavePrimary} className="fs3d-primary-save-btn">Save Primary Output</button>
                            </div>
                        </Html>

                        <ConnectionLine from={primaryNodePosition} to={sideNodePosition} color="#8fb1ff" />
                        <mesh position={sideNodePosition}>
                            <sphereGeometry args={[0.2, 14, 14]} />
                            <meshStandardMaterial color="#8fb1ff" emissive="#4f73dc" emissiveIntensity={0.4} />
                        </mesh>

                        <Html transform sprite position={[sideNodePosition[0], sideNodePosition[1] - 0.2, 0.2]} distanceFactor={12}>
                            <div className="fs3d-decision-center">
                                <div className="fs3d-decision-center-title">Decision + Change Log</div>
                                <div className="fs3d-decision-center-body">
                                    {decisionLog.slice(0, 8).map((line) => (
                                        <div key={line}>{line}</div>
                                    ))}
                                </div>
                            </div>
                        </Html>

                        <ConnectionLine from={guideAgentCenter} to={primaryNodePosition} color="#f9a8ff" />
                        <AgentRing center={guideAgentCenter} radius={3.2} color="#f9a8ff" label="Guide Agent" spin={1} />
                        <Html transform sprite position={[guideAgentCenter[0], guideAgentCenter[1] - 0.1, 0.2]} distanceFactor={12}>
                            <div className="fs3d-guide-agent-panel">
                                <div className="fs3d-guide-agent-title">Guide Agent</div>
                                <textarea
                                    className="fs3d-guide-agent-input"
                                    value={guideQuestion}
                                    onChange={(e) => setGuideQuestion(e.target.value)}
                                    placeholder="Ask for changes, clarifications, or refinements..."
                                />
                                <button onClick={handleGuideAssist} className="fs3d-guide-agent-btn">Apply Guided Change</button>
                            </div>
                        </Html>
                    </>
                ) : null}
            </Canvas>

            <div className="fs3d-galaxy-overlay">
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="fs3d-galaxy-header">
                    <div className="fs3d-diamond-hint">
                        {isPrimarySaved ? 'Diamond actions unlocked.' : 'Save Primary Output to unlock diamond actions.'}
                    </div>
                </motion.div>
            </div>
        </div>
    )
}

export default GalaxySetupScene
