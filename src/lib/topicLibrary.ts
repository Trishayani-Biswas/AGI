const TOPIC_SUBJECTS = [
  'Artificial intelligence',
  'Public education',
  'Digital privacy',
  'Climate policy',
  'Space exploration',
  'Biotechnology',
  'Remote work',
  'Cryptocurrency',
  'Universal basic income',
  'Social media',
  'Nuclear energy',
  'Autonomous vehicles',
  'Online speech regulation',
  'Healthcare systems',
  'Genetic editing',
  'Cybersecurity law',
  'Renewable infrastructure',
  'Global trade',
  'Immigration policy',
  'Judicial reform',
  'Military spending',
  'Urban planning',
  'Higher education',
  'Labor unions',
  'Gig economy platforms',
  'Data ownership',
  'AI in healthcare',
  'AI in courts',
  'Ocean conservation',
  'Food technology',
  'Fintech banking',
  'Surveillance technology',
  'Digital currencies',
  'Carbon markets',
  'STEM curriculum',
  'Ethical hacking',
  'Open-source software',
  'Platform moderation',
  'Elections security',
  'Public transport',
]

const TOPIC_ACTIONS = [
  'should be fully funded by governments',
  'should be mostly privatized',
  'should be globally regulated',
  'should be regulated nationally only',
  'should prioritize equity over efficiency',
  'should prioritize efficiency over equity',
  'should be mandatory in all major cities',
  'should be optional and market-driven',
  'should be adopted faster despite risks',
  'should be slowed until safety improves',
  'should be protected as a human right',
  'should require strict licensing',
  'should remain decentralized',
  'should be centralized for accountability',
  'should be open by default',
  'should remain closed for security',
  'should be taxed heavily',
  'should receive tax incentives',
  'should be handled by independent agencies',
  'should be handled directly by elected leaders',
]

const TOPIC_CONTEXTS = [
  'within the next decade',
  'for developing economies first',
  'for high-income countries first',
  'for younger generations only',
  'for all citizens equally',
  'to reduce long-term inequality',
  'to maximize economic growth',
  'to improve democratic trust',
  'to strengthen national security',
  'to reduce misinformation harms',
  'to improve public health outcomes',
  'to reduce environmental damage',
  'without increasing bureaucracy',
  'even if short-term costs are high',
  'even if growth slows temporarily',
]

const CURATED_TOPICS = [
  'AI will replace creative jobs',
  'Universal Basic Income is necessary',
  'Social media does more harm than good',
  'Space exploration is worth the cost',
  'Privacy matters more than security',
  'Remote work is the future',
  'Nuclear energy is essential for climate goals',
  'Cryptocurrency will replace traditional banking',
  'Countries should ban autonomous lethal weapons',
  'Human gene editing should be allowed for enhancement',
  'All elections should use paper ballots',
  'Internet access should be a constitutional right',
]

export function buildPresetTopics(targetCount = 1000): string[] {
  const topics = new Set<string>(CURATED_TOPICS)

  for (const subject of TOPIC_SUBJECTS) {
    for (const action of TOPIC_ACTIONS) {
      for (const context of TOPIC_CONTEXTS) {
        topics.add(`${subject} ${action} ${context}.`)
        if (topics.size >= targetCount) {
          return Array.from(topics)
        }
      }
    }
  }

  return Array.from(topics)
}
