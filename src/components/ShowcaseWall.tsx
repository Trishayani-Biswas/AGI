import signalNetworkImage from '../assets/signal-network.svg'
import adversarialFlowImage from '../assets/adversarial-flow.svg'
import confidenceRingsImage from '../assets/confidence-rings.svg'

const SHOWCASE_ITEMS = [
  {
    id: 'signal',
    title: 'Signal Constellation',
    detail: 'Realtime visual map of competing evidence paths.',
    image: signalNetworkImage
  },
  {
    id: 'adversarial',
    title: 'Adversarial Pipeline',
    detail: 'Structured flow from tension to resolution.',
    image: adversarialFlowImage
  },
  {
    id: 'confidence',
    title: 'Confidence Field',
    detail: 'Gradient confidence surface around arbitrator synthesis.',
    image: confidenceRingsImage
  }
]

export function ShowcaseWall() {
  return (
    <section className="showcase-wall reveal-section" aria-label="ARIA visual showcase">
      <div className="section-head">
        <h2>Visual Intelligence Surface</h2>
        <p>Editorial composition inspired by interactive studio landing pages.</p>
      </div>

      <div className="showcase-grid">
        {SHOWCASE_ITEMS.map((item, index) => (
          <article key={item.id} className={`showcase-card tilt-card reveal-section reveal-delay-${(index % 3) + 1}`}>
            <div className="showcase-media-wrap">
              <img src={item.image} alt={item.title} className="showcase-media" />
            </div>
            <div className="showcase-copy">
              <p className="showcase-index">0{index + 1}</p>
              <h3>{item.title}</h3>
              <p>{item.detail}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
