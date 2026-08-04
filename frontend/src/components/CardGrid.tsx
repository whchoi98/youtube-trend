import type { Card as CardData } from '../types'
import { Card } from './Card'

export function CardGrid({ cards }: { cards: CardData[] }) {
  return (
    <div className="card-grid">
      {cards.map((card) => (
        <Card key={card.videoId} card={card} />
      ))}
    </div>
  )
}

/** 로딩 중 표시하는 스켈레톤 카드 그리드(CSS pulse 애니메이션). */
export function CardSkeletonGrid({ count = 8 }: { count?: number }) {
  return (
    <div className="card-grid" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <div className="card skeleton" key={i}>
          <div className="card-thumb skeleton-block" />
          <div className="card-body">
            <div className="skeleton-line" />
            <div className="skeleton-line short" />
            <div className="skeleton-line shorter" />
          </div>
        </div>
      ))}
    </div>
  )
}
