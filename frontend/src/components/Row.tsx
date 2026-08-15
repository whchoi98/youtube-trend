import { useRef, useState } from 'react'
import type { HomeCard, HomeRow } from '../types'
import { formatCount } from '../format'

/** 배지 규약: baseline null=비교 불가(배지 없음), prevRank null=NEW,
 *  delta 양수=상승 ▲, 음수=하락 ▼, 0=유지 –. null vs 0 혼용 금지. */
function Badge({ card }: { card: HomeCard }) {
  if (card.baseline === null) return null
  if (card.prevRank === null) return <span className="badge new">NEW</span>
  if (card.delta !== null && card.delta > 0) return <span className="badge up">▲{card.delta}</span>
  if (card.delta !== null && card.delta < 0) return <span className="badge down">▼{-card.delta}</span>
  if (card.delta === 0) return <span className="badge same">–</span>
  return null
}

/** 좌측 상단 순위 칩 — 분야 행은 분야 내 순위, 나머지 행은 전체 순위다. */
function RankChip({ rank }: { rank: number }) {
  return <span className={rank <= 3 ? 'tile-rank top3' : 'tile-rank'}>{rank}</span>
}

function Velocity({ card }: { card: HomeCard }) {
  if (card.viewsPerHour === null || card.viewsPerHour <= 0) return null
  return <span className="vdelta"> +{formatCount(card.viewsPerHour)}/시</span>
}

function TagChips({ card }: { card: HomeCard }) {
  if (!card.tags) return null
  const chips = [...card.tags.topics, card.tags.age, card.tags.vibe].filter(
    (v): v is string => Boolean(v),
  )
  if (chips.length === 0) return null
  return (
    <div className="tagchips">
      {chips.map((c) => (
        <span key={c} className="tagchip">{c}</span>
      ))}
    </div>
  )
}

function Thumb({ card }: { card: HomeCard }) {
  const [failed, setFailed] = useState(false)
  if (failed || !card.thumbnail) return <div className="thumb-fallback" aria-hidden="true" />
  return <img src={card.thumbnail} alt="" loading="lazy" onError={() => setFailed(true)} />
}

function Tile({ card, onOpen }: { card: HomeCard; onOpen: (c: HomeCard) => void }) {
  return (
    <button type="button" className="tile" onClick={() => onOpen(card)}>
      <Thumb card={card} />
      <RankChip rank={card.rank} />
      <Badge card={card} />
      <span className="info">
        <span className="t">{card.title}</span>
        <span className="c">{card.channel}</span>
        <span className="hover-extra">
          <span className="n">
            조회 {formatCount(card.views)}<Velocity card={card} /> · 좋아요 {formatCount(card.likes)}
          </span>
          <TagChips card={card} />
        </span>
      </span>
    </button>
  )
}

/** TOP10 전용 — 넷플릭스식 큰 순위 숫자가 썸네일에 겹친다. */
function TopTile({ card, index, onOpen }: {
  card: HomeCard; index: number; onOpen: (c: HomeCard) => void
}) {
  return (
    <button type="button" className="tile top" onClick={() => onOpen(card)}>
      {/* 큰 숫자는 장식(aria-hidden) — 스크린리더에는 sr-only로 순위 전달 */}
      <span className="sr-only">{index + 1}위</span>
      <span className="bignum" aria-hidden="true">{index + 1}</span>
      <span className="thumbbox">
        <Thumb card={card} />
        <Badge card={card} />
        <span className="info">
          <span className="t">{card.title}</span>
          <span className="c">
            {card.channel} · {formatCount(card.views)}<Velocity card={card} />
          </span>
        </span>
      </span>
    </button>
  )
}

/** 가로 스트립 행 — 스크롤 스냅 + hover 화살표. */
export function Row({ row, hint, onTile }: {
  row: HomeRow
  hint?: string
  onTile: (c: HomeCard) => void
}) {
  const stripRef = useRef<HTMLDivElement>(null)
  const scroll = (dir: number) => {
    const el = stripRef.current
    if (!el) return
    // JS scrollBy의 behavior는 CSS reduced-motion 규칙을 우회하므로 직접 확인
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    el.scrollBy({ left: dir * el.clientWidth * 0.9, behavior: reduce ? 'auto' : 'smooth' })
  }

  return (
    <section className="row">
      <h2>
        {row.title}
        {hint && <span className="hint">{hint}</span>}
      </h2>
      <div className="strip-wrap">
        <button type="button" className="arrow l" aria-label="이전으로 스크롤" onClick={() => scroll(-1)}>‹</button>
        <div className="strip" ref={stripRef}>
          {row.items.map((c, i) =>
            row.kind === 'top10'
              ? <TopTile key={c.videoId} card={c} index={i} onOpen={onTile} />
              : <Tile key={c.videoId} card={c} onOpen={onTile} />,
          )}
        </div>
        <button type="button" className="arrow r" aria-label="다음으로 스크롤" onClick={() => scroll(1)}>›</button>
      </div>
    </section>
  )
}
