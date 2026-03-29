export type DecisionNodeType =
    | 'claim'
    | 'evidence'
    | 'assumption'
    | 'risk'
    | 'option'
    | 'cost'
    | 'stakeholder'
    | 'action'

export type DecisionEdgeRelation =
    | 'supports'
    | 'contradicts'
    | 'depends_on'
    | 'causes'
    | 'mitigates'

export interface DecisionNode {
    id: string
    type: DecisionNodeType
    title: string
    notes: string
    x: number
    y: number
    createdAt: number
}

export interface DecisionEdge {
    id: string
    from: string
    to: string
    relation: DecisionEdgeRelation
    createdAt: number
}

export interface DecisionGraph {
    id: string
    title: string
    createdAt: number
    nodes: DecisionNode[]
    edges: DecisionEdge[]
}

export interface DecisionGraphInsight {
    confidence: number
    uncertainty: number
    contradictionDensity: number
    blindSpots: string[]
    suggestedActions: string[]
}

const TYPE_WEIGHT: Record<DecisionNodeType, number> = {
    claim: 1.0,
    evidence: 1.35,
    assumption: 0.55,
    risk: 0.75,
    option: 1.0,
    cost: 0.8,
    stakeholder: 0.9,
    action: 1.1,
}

function clamp(value: number, min: number, max: number) {
    return Math.max(min, Math.min(max, value))
}

export function createDecisionNode(input: {
    type: DecisionNodeType
    title: string
    notes?: string
    x: number
    y: number
}): DecisionNode {
    return {
        id: `node-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        type: input.type,
        title: input.title.trim(),
        notes: (input.notes ?? '').trim(),
        x: input.x,
        y: input.y,
        createdAt: Date.now(),
    }
}

export function createDecisionEdge(input: {
    from: string
    to: string
    relation: DecisionEdgeRelation
}): DecisionEdge {
    return {
        id: `edge-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        from: input.from,
        to: input.to,
        relation: input.relation,
        createdAt: Date.now(),
    }
}

export function buildSeedDecisionGraph(): DecisionGraph {
    const now = Date.now()
    return {
        id: `graph-${now}`,
        title: 'Should we launch feature X in Q3?',
        createdAt: now,
        nodes: [
            { id: 'n1', type: 'claim', title: 'Feature X will increase retention', notes: '', x: 180, y: 120, createdAt: now },
            { id: 'n2', type: 'evidence', title: 'Pilot cohort improved D30 by 9%', notes: 'n=3,200 users', x: 460, y: 80, createdAt: now },
            { id: 'n3', type: 'risk', title: 'Onboarding complexity may increase churn', notes: '', x: 450, y: 260, createdAt: now },
            { id: 'n4', type: 'action', title: 'Run gated rollout to 15% traffic', notes: 'with rollback guardrails', x: 730, y: 160, createdAt: now },
            { id: 'n5', type: 'stakeholder', title: 'Support team capacity', notes: '', x: 700, y: 320, createdAt: now },
        ],
        edges: [
            { id: 'e1', from: 'n2', to: 'n1', relation: 'supports', createdAt: now },
            { id: 'e2', from: 'n3', to: 'n1', relation: 'contradicts', createdAt: now },
            { id: 'e3', from: 'n4', to: 'n3', relation: 'mitigates', createdAt: now },
            { id: 'e4', from: 'n5', to: 'n4', relation: 'depends_on', createdAt: now },
        ],
    }
}

export function analyzeDecisionGraph(graph: DecisionGraph): DecisionGraphInsight {
    const nodeCount = graph.nodes.length
    const edgeCount = graph.edges.length

    if (nodeCount === 0) {
        return {
            confidence: 10,
            uncertainty: 90,
            contradictionDensity: 0,
            blindSpots: ['No graph yet. Add a claim and at least one option.'],
            suggestedActions: ['Create your first claim node.'],
        }
    }

    const nodesById = new Map(graph.nodes.map((node) => [node.id, node]))
    const supports = graph.edges.filter((edge) => edge.relation === 'supports').length
    const contradicts = graph.edges.filter((edge) => edge.relation === 'contradicts').length
    const mitigates = graph.edges.filter((edge) => edge.relation === 'mitigates').length
    const evidenceCount = graph.nodes.filter((node) => node.type === 'evidence').length
    const riskCount = graph.nodes.filter((node) => node.type === 'risk').length
    const optionCount = graph.nodes.filter((node) => node.type === 'option').length
    const actionCount = graph.nodes.filter((node) => node.type === 'action').length

    const weightedNodeScore = graph.nodes.reduce((sum, node) => sum + TYPE_WEIGHT[node.type], 0)
    const edgeSignal = supports * 1.2 + mitigates * 0.9 - contradicts * 0.4

    const baseConfidence = (weightedNodeScore / Math.max(1, nodeCount)) * 34 + edgeSignal * 5 + evidenceCount * 4
    const confidence = Math.round(clamp(baseConfidence, 0, 100))

    const contradictionDensity = Math.round(clamp((contradicts / Math.max(1, edgeCount)) * 100, 0, 100))
    const uncertaintyRaw = 100 - confidence + contradictionDensity * 0.25 + Math.max(0, riskCount - mitigates) * 3
    const uncertainty = Math.round(clamp(uncertaintyRaw, 0, 100))

    const blindSpots: string[] = []
    if (evidenceCount === 0) blindSpots.push('No evidence nodes linked to your core claim.')
    if (optionCount === 0) blindSpots.push('No option nodes yet, so alternatives are underspecified.')
    if (actionCount === 0) blindSpots.push('No action nodes yet, so execution path is unclear.')

    const disconnectedNodes = graph.nodes.filter((node) => {
        const attached = graph.edges.some((edge) => edge.from === node.id || edge.to === node.id)
        return !attached
    })
    if (disconnectedNodes.length > 0) {
        blindSpots.push(`${disconnectedNodes.length} node(s) are disconnected from the decision flow.`)
    }

    const suggestedActions: string[] = []
    if (confidence < 55) suggestedActions.push('Increase confidence by adding more evidence and mitigation edges.')
    if (contradictionDensity > 35) suggestedActions.push('Resolve high contradictions by mapping direct mitigations or assumptions.')
    if (riskCount > 0 && mitigates < riskCount) suggestedActions.push('Add mitigation actions for each critical risk.')

    const topClaims = graph.nodes
        .filter((node) => node.type === 'claim' || node.type === 'option')
        .sort((a, b) => {
            const aSupport = graph.edges.filter((edge) => edge.to === a.id && edge.relation === 'supports').length
            const bSupport = graph.edges.filter((edge) => edge.to === b.id && edge.relation === 'supports').length
            return bSupport - aSupport
        })
        .slice(0, 2)

    if (topClaims.length > 0) {
        const labels = topClaims.map((node) => node.title).join(' | ')
        suggestedActions.push(`Current strongest candidate(s): ${labels}`)
    }

    const missingAssumptionChecks = graph.nodes.filter((node) => node.type === 'assumption').filter((assumption) => {
        return !graph.edges.some((edge) => edge.from === assumption.id && edge.relation === 'supports')
    })
    if (missingAssumptionChecks.length > 0) {
        suggestedActions.push(`${missingAssumptionChecks.length} assumption node(s) are unvalidated; add evidence links.`)
    }

    // Touch map lookup to ensure edge endpoints still exist and avoid stale references silently skewing metrics.
    const invalidEdges = graph.edges.filter((edge) => !nodesById.has(edge.from) || !nodesById.has(edge.to))
    if (invalidEdges.length > 0) {
        blindSpots.push(`${invalidEdges.length} edge(s) reference missing nodes.`)
    }

    return {
        confidence,
        uncertainty,
        contradictionDensity,
        blindSpots,
        suggestedActions,
    }
}
