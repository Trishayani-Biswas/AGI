const DOMAIN_BASELINES = [
    'Comparable systems usually require explicit monitoring and rollback criteria to remain safe.',
    'Evidence quality increases when claims are tied to reproducible metrics and longitudinal outcomes.',
    'Best practice favors staged deployment with periodic reassessment of assumptions.',
]

export const runDomainAgent = ({ topic, evidence }) => {
    const domainEvidence = evidence.slice(2, 5)
    const claims = domainEvidence.map((item, index) => ({
        id: `dom-${index + 1}`,
        side: 'baseline',
        text: `Domain baseline ${index + 1}: ${DOMAIN_BASELINES[index % DOMAIN_BASELINES.length]} For topic "${topic}", technical governance maturity is the key variable.`,
        evidenceIds: [item.id],
    }))

    return {
        summary: `Domain analysis frames "${topic}" as an execution and governance problem, not a binary yes/no choice.`,
        claims,
    }
}
