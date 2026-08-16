import { createPortal } from 'react-dom'
import type { HomeCard } from '../types'
import { formatCount } from '../format'

const WIDTH = 340

/** 타일 hover 시 뜨는 넷플릭스식 미리보기 박스 — 시각 전용(pointer-events 없음,
 *  클릭·hover는 밑의 타일이 계속 받는다). 스트립의 overflow에 잘리지 않도록
 *  body 포털 + fixed 좌표로 띄운다. */
export function PreviewCard({ card, anchor }: { card: HomeCard; anchor: DOMRect }) {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const width = Math.min(WIDTH, vw - 16)
  const left = Math.min(Math.max(anchor.left + anchor.width / 2 - width / 2, 8), vw - width - 8)
  // 타일보다 약간 위에서 시작해 확대된 느낌을 주되, 화면 위/아래를 벗어나지 않게
  const top = Math.min(Math.max(anchor.top - 70, 8), Math.max(8, vh - 400))

  const vph = card.viewsPerHour !== null && card.viewsPerHour > 0
    ? ` · +${formatCount(card.viewsPerHour)}/시` : ''
  const comment = card.tags?.comment
  const chips = card.tags
    ? [...card.tags.topics, card.tags.age, card.tags.vibe].filter((v): v is string => Boolean(v))
    : []

  return createPortal(
    <div className="preview-card" style={{ top, left, width }} role="presentation">
      {card.thumbnail && <img src={card.thumbnail} alt="" aria-hidden="true" />}
      <div className="pv-body">
        <div className="pv-title">{card.title}</div>
        <div className="pv-meta">
          {card.channel} · {card.category} · 조회 {formatCount(card.views)}{vph} · 좋아요 {formatCount(card.likes)}
        </div>
        {card.description && <p className="pv-desc">{card.description}</p>}
        {comment && (
          <div className="pv-ai">
            <span className="ai-chip">AI 브리핑</span>
            {comment}
          </div>
        )}
        {chips.length > 0 && (
          <div className="tagchips">
            {chips.map((c) => <span key={c} className="tagchip">{c}</span>)}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
