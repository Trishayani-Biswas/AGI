const FALLBACK_EVIDENCE = [
    {
        source: 'OECD Policy Observatory',
        url: 'https://example.local/oecd-policy-observatory',
        title: 'Policy trade-off patterns in emerging technology governance',
        excerpt: 'Early policy design failures are often caused by weak incentive alignment and delayed measurement planning.',
        tags: ['policy', 'governance', 'measurement'],
    },
    {
        source: 'NIST Practice Notes',
        url: 'https://example.local/nist-practice-notes',
        title: 'Risk baselines for complex socio-technical systems',
        excerpt: 'Teams that define clear risk ownership upfront ship with lower incident severity in year one.',
        tags: ['risk', 'safety', 'operations'],
    },
    {
        source: 'WHO Public Guidance Digest',
        url: 'https://example.local/who-guidance-digest',
        title: 'Public communication and trust dynamics',
        excerpt: 'Policy trust degrades when outcomes are not monitored with transparent indicators.',
        tags: ['public trust', 'communication', 'outcomes'],
    },
    {
        source: 'IEEE Systems Review',
        url: 'https://example.local/ieee-systems-review',
        title: 'Failure modes in rapidly scaled deployments',
        excerpt: 'Scale amplifies edge-case failures when safeguards are designed for pilot conditions only.',
        tags: ['engineering', 'scale', 'reliability'],
    },
    {
        source: 'arXiv Survey Archive',
        url: 'https://example.local/arxiv-survey-archive',
        title: 'Evaluation methods for model-assisted decision support',
        excerpt: 'Benchmark improvements do not guarantee real-world benefit without task-level calibration checks.',
        tags: ['evaluation', 'benchmarks', 'calibration'],
    },
    {
        source: 'World Bank Insights',
        url: 'https://example.local/world-bank-insights',
        title: 'Distributional effects in policy interventions',
        excerpt: 'Average gains can hide concentrated losses among subgroups with low implementation access.',
        tags: ['equity', 'distribution', 'economics'],
    },
    {
        source: 'Nature Commentary',
        url: 'https://example.local/nature-commentary',
        title: 'Scientific uncertainty communication in public tools',
        excerpt: 'Decision quality improves when uncertainty is explicit rather than hidden behind confidence theater.',
        tags: ['uncertainty', 'science communication', 'decision quality'],
    },
    {
        source: 'ACM Field Report',
        url: 'https://example.local/acm-field-report',
        title: 'Operational debt in intelligence workflows',
        excerpt: 'Systems with no contradiction review loop accumulate hidden debt that surfaces as delayed failures.',
        tags: ['operations', 'workflow', 'quality'],
    },
]

const deterministicHash = (value) => {
    let hash = 0
    for (let i = 0; i < value.length; i += 1) {
        hash = (hash * 31 + value.charCodeAt(i)) >>> 0
    }
    return hash
}

export const buildEvidenceForTopic = (topic, limit = 6) => {
    const safeTopic = typeof topic === 'string' ? topic.trim() : ''
    const normalized = safeTopic.toLowerCase() || 'general research question'
    const size = Math.max(3, Math.min(10, Number.isFinite(limit) ? Math.round(limit) : 6))
    const start = deterministicHash(normalized) % FALLBACK_EVIDENCE.length

    return Array.from({ length: size }, (_, index) => {
        const base = FALLBACK_EVIDENCE[(start + index) % FALLBACK_EVIDENCE.length]
        return {
            id: `ev-${index + 1}`,
            source: base.source,
            url: base.url,
            title: base.title,
            excerpt: `${base.excerpt} Topic link: ${safeTopic || 'general research question'}.`,
            relevance: Math.max(52, 90 - index * 5),
            tags: base.tags,
        }
    })
}
