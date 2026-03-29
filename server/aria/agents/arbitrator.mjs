const scoreClaim = (claim, evidenceById) => {
    const evidenceCount = Array.isArray(claim.evidenceIds) ? claim.evidenceIds.length : 0
    const hasValidEvidence = evidenceCount > 0 && claim.evidenceIds.every((id) => Boolean(evidenceById.get(id)))
    const sideWeight = claim.side === 'baseline' ? 6 : claim.side === 'support' ? 4 : 2
    const evidenceWeight = evidenceCount * 14
    const confidence = Math.max(35, Math.min(92, 42 + evidenceWeight + sideWeight + (hasValidEvidence ? 10 : -12)))
    return confidence
}

export const runArbitratorAgent = ({ topic, evidence, advocate, skeptic, domain }) => {
    const evidenceById = new Map(evidence.map((item) => [item.id, item]))
    const allClaims = [...advocate.claims, ...skeptic.claims, ...domain.claims]

    const claims = allClaims.map((claim) => ({
        ...claim,
        confidence: scoreClaim(claim, evidenceById),
        contradictions: claim.side === 'support' ? ['skeptic'] : claim.side === 'challenge' ? ['advocate'] : [],
    }))

    const contradictions = [
        {
            id: 'ctr-1',
            statement: 'Projected upside depends on assumptions that skeptic evidence contests under real deployment constraints.',
            involvedClaimIds: [claims[0]?.id, claims[3]?.id].filter(Boolean),
        },
        {
            id: 'ctr-2',
            statement: 'Aggregate benefit framing conflicts with subgroup-risk findings from domain/equity evidence.',
            involvedClaimIds: [claims[1]?.id, claims[5]?.id].filter(Boolean),
        },
    ]

    const knowledgeGaps = [
        `No strong longitudinal dataset was established yet for "${topic}" across diverse geographies.`,
        'Unclear threshold for acceptable downside risk under worst-case implementation behavior.',
        'Limited evidence on how outcomes change after initial novelty effects decay.',
    ]

    return {
        claims,
        contradictions,
        knowledgeGaps,
        summary: `Arbitrator concludes "${topic}" is promising but contingent: confidence is moderate-to-high only when governance controls and measurement discipline are explicit.`,
    }
}
