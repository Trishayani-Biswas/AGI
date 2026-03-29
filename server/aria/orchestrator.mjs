import { buildEvidenceForTopic } from './knowledgeBase.mjs'
import { runAdvocateAgent } from './agents/advocate.mjs'
import { runSkepticAgent } from './agents/skeptic.mjs'
import { runDomainAgent } from './agents/domain.mjs'
import { runArbitratorAgent } from './agents/arbitrator.mjs'

const MAX_TOPIC_LENGTH = 240

export const normalizeResearchRequest = (payload) => {
    const topicRaw = typeof payload?.topic === 'string' ? payload.topic.trim() : ''
    const topic = topicRaw.slice(0, MAX_TOPIC_LENGTH)
    const depthRaw = typeof payload?.depth === 'string' ? payload.depth.trim().toLowerCase() : 'standard'
    const depth = ['quick', 'standard', 'deep'].includes(depthRaw) ? depthRaw : 'standard'
    const maxSourcesRaw = Number(payload?.maxSources)
    const maxSources = Math.min(10, Math.max(3, Number.isFinite(maxSourcesRaw) ? Math.round(maxSourcesRaw) : 6))

    return {
        topic,
        depth,
        maxSources,
    }
}

export const runAriaResearch = async (request) => {
    const evidence = buildEvidenceForTopic(request.topic, request.maxSources)

    const [advocate, skeptic, domain] = await Promise.all([
        Promise.resolve(runAdvocateAgent({ topic: request.topic, evidence })),
        Promise.resolve(runSkepticAgent({ topic: request.topic, evidence })),
        Promise.resolve(runDomainAgent({ topic: request.topic, evidence })),
    ])

    const arbitrator = runArbitratorAgent({
        topic: request.topic,
        evidence,
        advocate,
        skeptic,
        domain,
    })

    return {
        topic: request.topic,
        depth: request.depth,
        agents: {
            advocate,
            skeptic,
            domain,
            arbitrator: {
                summary: arbitrator.summary,
            },
        },
        claims: arbitrator.claims,
        contradictions: arbitrator.contradictions,
        knowledgeGaps: arbitrator.knowledgeGaps,
        evidence,
        metadata: {
            sourceMode: 'deterministic-fallback-v1',
            generatedAt: new Date().toISOString(),
            maxSources: request.maxSources,
        },
    }
}
