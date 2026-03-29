const SKEPTIC_PATTERNS = [
    'Observed gains may be overstated when rollout conditions differ from pilot assumptions.',
    'Without accountability, second-order harms can offset first-order improvements.',
    'Distributional effects often create hidden losers despite positive aggregate metrics.',
]

export const runSkepticAgent = ({ topic, evidence }) => {
    const skepticalEvidence = evidence.slice(1, 4)
    const claims = skepticalEvidence.map((item, index) => ({
        id: `skp-${index + 1}`,
        side: 'challenge',
        text: `Challenge claim ${index + 1}: ${SKEPTIC_PATTERNS[index % SKEPTIC_PATTERNS.length]} For topic "${topic}", risk concentration remains under-specified.`,
        evidenceIds: [item.id],
    }))

    return {
        summary: `Skeptic flags material uncertainty on "${topic}" around scale, fairness, and operational resilience.`,
        claims,
    }
}
