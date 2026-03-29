import { describe, expect, it } from 'vitest'
import {
    analyzeDecisionGraph,
    buildSeedDecisionGraph,
    createDecisionEdge,
    createDecisionNode,
    type DecisionGraph,
} from './decisionGraph'

describe('decisionGraph', () => {
    it('creates nodes and edges with expected fields', () => {
        const node = createDecisionNode({
            type: 'claim',
            title: 'Adopt model-based deployment',
            x: 12,
            y: 44,
        })

        expect(node.id).toContain('node-')
        expect(node.title).toBe('Adopt model-based deployment')

        const edge = createDecisionEdge({ from: 'n1', to: 'n2', relation: 'supports' })
        expect(edge.id).toContain('edge-')
        expect(edge.relation).toBe('supports')
    })

    it('analyzes an empty graph safely', () => {
        const graph: DecisionGraph = {
            id: 'g-empty',
            title: 'empty',
            createdAt: Date.now(),
            nodes: [],
            edges: [],
        }

        const insight = analyzeDecisionGraph(graph)
        expect(insight.confidence).toBe(10)
        expect(insight.uncertainty).toBe(90)
        expect(insight.blindSpots.length).toBeGreaterThan(0)
    })

    it('returns bounded metrics for seed graph', () => {
        const graph = buildSeedDecisionGraph()
        const insight = analyzeDecisionGraph(graph)

        expect(insight.confidence).toBeGreaterThanOrEqual(0)
        expect(insight.confidence).toBeLessThanOrEqual(100)
        expect(insight.uncertainty).toBeGreaterThanOrEqual(0)
        expect(insight.uncertainty).toBeLessThanOrEqual(100)
        expect(insight.contradictionDensity).toBeGreaterThanOrEqual(0)
        expect(insight.contradictionDensity).toBeLessThanOrEqual(100)
    })
})
