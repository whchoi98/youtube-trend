import { useState } from 'react'
import type { Card as CardData } from '../types'
import { CategoryBadge, DeltaBadge, velocityText } from './Badge'
import { formatCount } from '../format'

const RANK_CLASS: Record<number, string> = { 1: 'rank-1', 2: 'rank-2', 3: 'rank-3' }

export function Card({ card }: { card: CardData }) {
  const [thumbFailed, setThumbFailed] = useState(false)
  const vt = velocityText(card.viewsPerHour)
  const rankClass = RANK_CLASS[card.rank] ?? ''

  return (
    <a
      className="card"
      href={`https://www.youtube.com/watch?v=${card.videoId}`}
      target="_blank"
      rel="noopener noreferrer"
    >
      <div className="card-thumb-wrap">
        {thumbFailed ? (
          <div className="card-thumb card-thumb-fallback" aria-hidden="true" />
        ) : (
          <img
            className="card-thumb"
            src={card.thumbnail}
            alt=""
            loading="lazy"
            onError={() => setThumbFailed(true)}
          />
        )}
        <span className={`rank-badge ${rankClass}`}>{card.rank}</span>
        <div className="delta-slot">
          <DeltaBadge c={card} />
        </div>
      </div>
      <div className="card-body">
        <h3 className="card-title">{card.title}</h3>
        <p className="card-channel">{card.channel}</p>
        <div className="card-stats">
          <span>조회수 {formatCount(card.views)}</span>
          <span>좋아요 {formatCount(card.likes)}</span>
        </div>
        <div className="card-footer">
          <CategoryBadge name={card.category} />
          {vt !== null && (
            <span className="velocity" role="img" aria-label={`시간당 조회수 변화 ${vt}`}>
              {vt}
            </span>
          )}
        </div>
      </div>
    </a>
  )
}
