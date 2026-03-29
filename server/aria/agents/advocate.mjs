const ADVOCATE_PATTERNS = [
    'Strong implementation can create measurable upside if guardrails are explicit from day one.',
    'When incentives are aligned, adoption quality tends to improve across execution environments.',
    'Early-stage pilots indicate value when outcomes are tracked with concrete metrics.',
]

export const runAdvocateAgent = ({ topic, evidence }) => {
    const topEvidence = evidence.slice(0, 3)
    const claims = topEvidence.map((item, index) => ({
        id: `adv-${index + 1}`,
        side: 'support',
        text: `Support claim ${index + 1}: ${ADVOCATE_PATTERNS[index % ADVOCATE_PATTERNS.length]} For topic "${topic}", source signals favor cautious expansion.`,
        evidenceIds: [item.id],
    }))

    return {
        summary: `Advocate finds practical upside on "${topic}" with controlled rollout and measurable checkpoints.`,
        claims,
    }
}
