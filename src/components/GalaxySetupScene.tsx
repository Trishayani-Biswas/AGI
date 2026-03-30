import { type FormEvent, useState } from 'react'

type ResearchDepth = 'quick' | 'standard' | 'deep'

interface GalaxySetupProps {
  onSelectTopic: (topic: string) => void
  onStartResearch: (config: { topic: string; depth: ResearchDepth; maxSources: number }) => void
  onStartDecisionGraph: () => void
  presetTopics?: string[]
}

// Legacy compatibility component retained so existing imports remain valid.
// The primary app flow now lives in FlipSide3D.
export function GalaxySetupScene({ onSelectTopic, onStartResearch, presetTopics = [] }: GalaxySetupProps) {
  const [topic, setTopic] = useState(presetTopics[0] ?? '')
  const [depth, setDepth] = useState<ResearchDepth>('standard')
  const [maxSources, setMaxSources] = useState(6)

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const nextTopic = topic.trim()
    if (!nextTopic) return
    onSelectTopic(nextTopic)
    onStartResearch({ topic: nextTopic, depth, maxSources })
  }

  return (
    <section className="fs3d-legacy-shell" aria-label="Legacy setup">
      <h2 className="fs3d-legacy-title">Legacy Galaxy Setup</h2>
      <form className="fs3d-legacy-form" onSubmit={handleSubmit}>
        <label htmlFor="legacy-topic" className="fs3d-legacy-label">Topic</label>
        <input
          id="legacy-topic"
          className="fs3d-legacy-input"
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          placeholder="Enter a topic"
        />

        <label htmlFor="legacy-depth" className="fs3d-legacy-label">Depth</label>
        <select
          id="legacy-depth"
          className="fs3d-legacy-input"
          value={depth}
          onChange={(event) => setDepth(event.target.value as ResearchDepth)}
        >
          <option value="quick">Quick</option>
          <option value="standard">Standard</option>
          <option value="deep">Deep</option>
        </select>

        <label htmlFor="legacy-sources" className="fs3d-legacy-label">Sources</label>
        <select
          id="legacy-sources"
          className="fs3d-legacy-input"
          value={maxSources}
          onChange={(event) => setMaxSources(Number(event.target.value))}
        >
          <option value={4}>4</option>
          <option value={6}>6</option>
          <option value={8}>8</option>
        </select>

        <button type="submit" className="fs3d-legacy-button">Start Research</button>
      </form>
    </section>
  )
}
