import { useMemo, useRef, useState } from 'react'
import {
    analyzeDecisionGraph,
    buildSeedDecisionGraph,
    createDecisionEdge,
    createDecisionNode,
    type DecisionEdgeRelation,
    type DecisionGraph,
    type DecisionNodeType,
} from '../lib/decisionGraph'
import type { AriaResearchRun } from '../lib/backendClient'

type Placement = { x: number; y: number } | null

const NODE_TYPES: Array<{ id: DecisionNodeType; label: string }> = [
    { id: 'claim', label: 'Claim' },
    { id: 'evidence', label: 'Evidence' },
    { id: 'assumption', label: 'Assumption' },
    { id: 'risk', label: 'Risk' },
    { id: 'option', label: 'Option' },
    { id: 'cost', label: 'Cost' },
    { id: 'stakeholder', label: 'Stakeholder' },
    { id: 'action', label: 'Action' },
]

const EDGE_RELATIONS: Array<{ id: DecisionEdgeRelation; label: string }> = [
    { id: 'supports', label: 'Supports' },
    { id: 'contradicts', label: 'Contradicts' },
    { id: 'depends_on', label: 'Depends On' },
    { id: 'causes', label: 'Causes' },
    { id: 'mitigates', label: 'Mitigates' },
]

interface DecisionGraphSceneProps {
    onBack: () => void
    researchRun?: AriaResearchRun | null
}

function buildGraphFromResearchRun(run: AriaResearchRun): DecisionGraph {
    const now = Date.now()
    const graph: DecisionGraph = {
        id: `graph-${now}`,
        title: `ARIA Decision Graph: ${run.topic}`,
        createdAt: now,
        nodes: [],
        edges: [],
    }

    const nodeIdByRef = new Map<string, string>()

    run.claims.forEach((claim, index) => {
        const node = createDecisionNode({
            type: claim.side === 'challenge' ? 'risk' : claim.side === 'baseline' ? 'assumption' : 'claim',
            title: claim.text,
            notes: `confidence=${claim.confidence}`,
            x: 170 + (index % 3) * 260,
            y: 120 + Math.floor(index / 3) * 110,
        })
        graph.nodes.push(node)
        nodeIdByRef.set(claim.id, node.id)
    })

    run.evidence.slice(0, 9).forEach((evidence, index) => {
        const node = createDecisionNode({
            type: 'evidence',
            title: evidence.title,
            notes: evidence.source,
            x: 120 + (index % 3) * 260,
            y: 500 + Math.floor(index / 3) * 92,
        })
        graph.nodes.push(node)
        nodeIdByRef.set(evidence.id, node.id)
    })

    run.claims.forEach((claim) => {
        const claimNodeId = nodeIdByRef.get(claim.id)
        if (!claimNodeId) return

        claim.evidenceIds.forEach((evidenceId) => {
            const evidenceNodeId = nodeIdByRef.get(evidenceId)
            if (!evidenceNodeId) return
            graph.edges.push(createDecisionEdge({
                from: evidenceNodeId,
                to: claimNodeId,
                relation: claim.side === 'challenge' ? 'contradicts' : 'supports',
            }))
        })
    })

    return graph
}

export function DecisionGraphScene({ onBack, researchRun }: DecisionGraphSceneProps) {
    const [graph, setGraph] = useState<DecisionGraph>(() => researchRun ? buildGraphFromResearchRun(researchRun) : buildSeedDecisionGraph())
    const [newNodeTitle, setNewNodeTitle] = useState('')
    const [newNodeNotes, setNewNodeNotes] = useState('')
    const [newNodeType, setNewNodeType] = useState<DecisionNodeType>('claim')
    const [pendingPlacement, setPendingPlacement] = useState<Placement>(null)
    const [sourceNodeId, setSourceNodeId] = useState<string>('')
    const [targetNodeId, setTargetNodeId] = useState<string>('')
    const [relation, setRelation] = useState<DecisionEdgeRelation>('supports')
    const [selectedNodeId, setSelectedNodeId] = useState<string>('')
    const [error, setError] = useState('')
    const canvasRef = useRef<HTMLDivElement | null>(null)

    const insight = useMemo(() => analyzeDecisionGraph(graph), [graph])
    const selectedNode = useMemo(() => graph.nodes.find((node) => node.id === selectedNodeId) ?? null, [graph.nodes, selectedNodeId])

    const startNodePlacement = () => {
        if (!newNodeTitle.trim()) {
            setError('Node title is required before placement.')
            return
        }
        setError('')
        setPendingPlacement({ x: 80, y: 80 })
    }

    const handleCanvasClick = (event: React.MouseEvent<HTMLDivElement>) => {
        if (!pendingPlacement || !canvasRef.current) return

        const bounds = canvasRef.current.getBoundingClientRect()
        const x = event.clientX - bounds.left
        const y = event.clientY - bounds.top

        const node = createDecisionNode({
            type: newNodeType,
            title: newNodeTitle,
            notes: newNodeNotes,
            x,
            y,
        })

        setGraph((prev) => ({ ...prev, nodes: [...prev.nodes, node] }))
        setPendingPlacement(null)
        setNewNodeTitle('')
        setNewNodeNotes('')
    }

    const handleAddEdge = () => {
        if (!sourceNodeId || !targetNodeId) {
            setError('Select source and target nodes before creating an edge.')
            return
        }
        if (sourceNodeId === targetNodeId) {
            setError('Source and target must be different.')
            return
        }

        const duplicate = graph.edges.some(
            (edge) => edge.from === sourceNodeId && edge.to === targetNodeId && edge.relation === relation,
        )
        if (duplicate) {
            setError('This exact edge already exists.')
            return
        }

        const edge = createDecisionEdge({ from: sourceNodeId, to: targetNodeId, relation })
        setGraph((prev) => ({ ...prev, edges: [...prev.edges, edge] }))
        setError('')
    }

    const removeSelectedNode = () => {
        if (!selectedNodeId) return
        setGraph((prev) => ({
            ...prev,
            nodes: prev.nodes.filter((node) => node.id !== selectedNodeId),
            edges: prev.edges.filter((edge) => edge.from !== selectedNodeId && edge.to !== selectedNodeId),
        }))
        setSelectedNodeId('')
    }

    const resetGraph = () => {
        setGraph(researchRun ? buildGraphFromResearchRun(researchRun) : buildSeedDecisionGraph())
        setSelectedNodeId('')
        setError('')
    }

    return (
        <div className="dig-root">
            <div className="dig-topbar">
                <button onClick={onBack} className="dig-topbar-btn">
                    Back To Galaxy
                </button>
                <div className="dig-title-wrap">
                    <h1 className="dig-title">Decision Intelligence Graph</h1>
                    <p className="dig-subtitle">Map ARIA claims, evidence, risks, and actions to produce actionable decisions.</p>
                </div>
                <button onClick={resetGraph} className="dig-topbar-btn dig-topbar-btn-alt">
                    Reset Seed
                </button>
            </div>

            <div className="dig-layout">
                <aside className="dig-panel dig-panel-left">
                    <h2 className="dig-panel-title">Node Builder</h2>

                    <label className="dig-label">Node Type</label>
                    <select
                        title="Node type"
                        aria-label="Node type"
                        className="dig-select"
                        value={newNodeType}
                        onChange={(event) => setNewNodeType(event.target.value as DecisionNodeType)}
                    >
                        {NODE_TYPES.map((type) => (
                            <option key={type.id} value={type.id}>
                                {type.label}
                            </option>
                        ))}
                    </select>

                    <label className="dig-label">Title</label>
                    <input
                        className="dig-input"
                        value={newNodeTitle}
                        onChange={(event) => setNewNodeTitle(event.target.value)}
                        placeholder="e.g. Pilot proves retention gain"
                    />

                    <label className="dig-label">Notes</label>
                    <textarea
                        className="dig-textarea"
                        value={newNodeNotes}
                        onChange={(event) => setNewNodeNotes(event.target.value)}
                        placeholder="Optional assumptions or data source"
                    />

                    <button onClick={startNodePlacement} className="dig-primary-btn">
                        Place Node On Canvas
                    </button>

                    <h3 className="dig-section-title">Selected Node</h3>
                    {selectedNode ? (
                        <div className="dig-node-card">
                            <p className="dig-node-type">{selectedNode.type}</p>
                            <h4 className="dig-node-title">{selectedNode.title}</h4>
                            {selectedNode.notes ? <p className="dig-node-notes">{selectedNode.notes}</p> : <p className="dig-node-notes">No notes</p>}
                            <button onClick={removeSelectedNode} className="dig-danger-btn">
                                Remove Node
                            </button>
                        </div>
                    ) : (
                        <p className="dig-empty-copy">Select a node from the canvas.</p>
                    )}

                    {error ? <p className="dig-error">{error}</p> : null}
                </aside>

                <main className="dig-canvas-wrap">
                    <div className="dig-canvas-hint">
                        {pendingPlacement
                            ? 'Click anywhere on the canvas to place the pending node.'
                            : 'Click a node to inspect it, then connect nodes from the right panel.'}
                    </div>
                    <div ref={canvasRef} className="dig-canvas" onClick={handleCanvasClick}>
                        <svg className="dig-edge-layer" width="100%" height="100%" aria-hidden="true">
                            {graph.edges.map((edge) => {
                                const from = graph.nodes.find((node) => node.id === edge.from)
                                const to = graph.nodes.find((node) => node.id === edge.to)
                                if (!from || !to) return null
                                return (
                                    <g key={edge.id}>
                                        <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} className={`dig-edge dig-edge-${edge.relation}`} />
                                        <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2} className="dig-edge-label">
                                            {edge.relation.replace('_', ' ')}
                                        </text>
                                    </g>
                                )
                            })}
                            {graph.nodes.map((node) => (
                                <g
                                    key={node.id}
                                    className={`dig-node-svg dig-node-${node.type} ${selectedNodeId === node.id ? 'is-selected' : ''}`}
                                    onClick={(event) => {
                                        event.stopPropagation()
                                        setSelectedNodeId(node.id)
                                    }}
                                >
                                    <rect x={node.x - 82} y={node.y - 20} width={164} height={40} rx={12} ry={12} className="dig-node-rect" />
                                    <text x={node.x} y={node.y + 5} textAnchor="middle" className="dig-node-name">
                                        {node.title.length > 26 ? `${node.title.slice(0, 23)}...` : node.title}
                                    </text>
                                </g>
                            ))}
                        </svg>
                    </div>
                </main>

                <aside className="dig-panel dig-panel-right">
                    <h2 className="dig-panel-title">Edge Composer</h2>

                    <label className="dig-label">Source</label>
                    <select
                        title="Edge source"
                        aria-label="Edge source"
                        className="dig-select"
                        value={sourceNodeId}
                        onChange={(event) => setSourceNodeId(event.target.value)}
                    >
                        <option value="">Select source</option>
                        {graph.nodes.map((node) => (
                            <option key={node.id} value={node.id}>
                                {node.title}
                            </option>
                        ))}
                    </select>

                    <label className="dig-label">Relation</label>
                    <select
                        title="Edge relation"
                        aria-label="Edge relation"
                        className="dig-select"
                        value={relation}
                        onChange={(event) => setRelation(event.target.value as DecisionEdgeRelation)}
                    >
                        {EDGE_RELATIONS.map((item) => (
                            <option key={item.id} value={item.id}>
                                {item.label}
                            </option>
                        ))}
                    </select>

                    <label className="dig-label">Target</label>
                    <select
                        title="Edge target"
                        aria-label="Edge target"
                        className="dig-select"
                        value={targetNodeId}
                        onChange={(event) => setTargetNodeId(event.target.value)}
                    >
                        <option value="">Select target</option>
                        {graph.nodes.map((node) => (
                            <option key={node.id} value={node.id}>
                                {node.title}
                            </option>
                        ))}
                    </select>

                    <button onClick={handleAddEdge} className="dig-primary-btn">
                        Add Edge
                    </button>

                    <h3 className="dig-section-title">Graph Insight</h3>
                    <div className="dig-metric-grid">
                        <div className="dig-metric">
                            <span className="dig-metric-label">Confidence</span>
                            <strong className="dig-metric-value">{insight.confidence}%</strong>
                        </div>
                        <div className="dig-metric">
                            <span className="dig-metric-label">Uncertainty</span>
                            <strong className="dig-metric-value">{insight.uncertainty}%</strong>
                        </div>
                        <div className="dig-metric">
                            <span className="dig-metric-label">Contradictions</span>
                            <strong className="dig-metric-value">{insight.contradictionDensity}%</strong>
                        </div>
                    </div>

                    <h4 className="dig-list-title">Blind Spots</h4>
                    <ul className="dig-list">
                        {insight.blindSpots.length > 0 ? (
                            insight.blindSpots.map((item) => <li key={item}>{item}</li>)
                        ) : (
                            <li>No major blind spots detected.</li>
                        )}
                    </ul>

                    <h4 className="dig-list-title">Suggested Actions</h4>
                    <ul className="dig-list">
                        {insight.suggestedActions.length > 0 ? (
                            insight.suggestedActions.map((item) => <li key={item}>{item}</li>)
                        ) : (
                            <li>Keep refining your graph.</li>
                        )}
                    </ul>
                </aside>
            </div>
        </div>
    )
}

export default DecisionGraphScene
