import { useEffect, useRef, useState } from 'react'
import type { HomeCard, HomeRow } from '../types'
import { formatCount } from '../format'
import { PreviewCard } from './PreviewCard'

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

function Velocity({ card }: { card: HomeCard }) {
  if (card.viewsPerHour === null || card.viewsPerHour <= 0) return null
  return <span className="vdelta"> +{formatCount(card.viewsPerHour)}/시</span>
}

/** 좌측 상단 순위 칩 — 분야 행은 분야 내 순위, 나머지 행은 전체 순위다. */
function RankChip({ rank }: { rank: number }) {
  return <span className={rank <= 3 ? 'tile-rank top3' : 'tile-rank'}>{rank}</span>
}

function Thumb({ card }: { card: HomeCard }) {
  const [failed, setFailed] = useState(false)
  if (failed || !card.thumbnail) return <div className="thumb-fallback" aria-hidden="true" />
  return <img src={card.thumbnail} alt="" loading="lazy" onError={() => setFailed(true)} />
}

type HoverHandlers = {
  onEnter: (card: HomeCard, el: HTMLElement) => void
  onLeave: () => void
}

function Tile({ card, onOpen, hover }: {
  card: HomeCard
  onOpen: (c: HomeCard) => void
  hover: HoverHandlers
}) {
  return (
    <button
      type="button"
      className="tile"
      onClick={() => onOpen(card)}
      onMouseEnter={(e) => hover.onEnter(card, e.currentTarget)}
      onMouseLeave={hover.onLeave}
      onFocus={(e) => hover.onEnter(card, e.currentTarget)}
      onBlur={hover.onLeave}
    >
      <Thumb card={card} />
      <RankChip rank={card.rank} />
      <Badge card={card} />
      <span className="info">
        <span className="t">{card.title}</span>
        <span className="c">{card.channel}</span>
        <span className="n">
          조회 {formatCount(card.views)}<Velocity card={card} />
        </span>
      </span>
    </button>
  )
}

/** TOP10 전용 — 넷플릭스식 큰 순위 숫자가 썸네일에 겹친다. */
function TopTile({ card, index, onOpen, hover }: {
  card: HomeCard
  index: number
  onOpen: (c: HomeCard) => void
  hover: HoverHandlers
}) {
  return (
    <button
      type="button"
      className="tile top"
      onClick={() => onOpen(card)}
      onMouseEnter={(e) => hover.onEnter(card, e.currentTarget)}
      onMouseLeave={hover.onLeave}
      onFocus={(e) => hover.onEnter(card, e.currentTarget)}
      onBlur={hover.onLeave}
    >
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

const HOVER_DELAY_MS = 350

/** hover 미리보기는 정밀 포인터 전용 — 터치 탭(에뮬레이트 mouseenter/focus)에
 *  팝오버가 붙어 떨어지지 않는 것을 막는다. 호출 시점 평가(입력 장치 변경 대응). */
const canHover = () =>
  window.matchMedia('(hover: hover) and (pointer: fine)').matches

/** 가로 스트립 행 — 스크롤 스냅 + hover 화살표 + 넷플릭스식 미리보기 박스.
 *  미리보기는 지연(350ms) 후 타일 위에 별도 박스로 뜬다(간략 정보 + AI 브리핑).
 *  limit: 홈 표시용 절단(예: top10 행은 20개를 싣고 홈에서는 10개만). */
export function Row({ row, hint, onTile, limit }: {
  row: HomeRow
  hint?: string
  onTile: (c: HomeCard) => void
  limit?: number
}) {
  const stripRef = useRef<HTMLDivElement>(null)
  const [preview, setPreview] = useState<{ card: HomeCard; anchor: DOMRect } | null>(null)
  const timerRef = useRef<number | null>(null)

  const clearTimer = () => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }
  const hover: HoverHandlers = {
    onEnter: (card, el) => {
      if (!canHover()) return
      clearTimer()
      timerRef.current = window.setTimeout(() => {
        // 60초 폴링 재렌더로 타일이 교체됐으면 분리된 rect를 쓰지 않는다
        if (!el.isConnected) return
        setPreview({ card, anchor: el.getBoundingClientRect() })
      }, HOVER_DELAY_MS)
    },
    onLeave: () => {
      clearTimer()
      setPreview(null)
    },
  }
  useEffect(() => clearTimer, [])

  // 페이지/중첩 컨테이너 스크롤·리사이즈 시 앵커 좌표가 낡는다 — 열려 있으면 닫는다.
  // scroll은 버블되지 않으므로 캡처로 잡아야 스트립 가로 스크롤까지 커버된다.
  useEffect(() => {
    if (!preview) return
    const close = () => setPreview(null)
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    window.addEventListener('scroll', close, { capture: true, passive: true })
    window.addEventListener('resize', close)
    document.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('scroll', close, { capture: true })
      window.removeEventListener('resize', close)
      document.removeEventListener('keydown', onKey)
    }
  }, [preview])

  // 폴링으로 행 구성이 바뀌어 hover 중인 카드가 사라지면 유령 팝오버를 정리한다
  useEffect(() => {
    setPreview((prev) =>
      prev && !row.items.some((c) => c.videoId === prev.card.videoId) ? null : prev)
  }, [row.items])

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
          {(limit ? row.items.slice(0, limit) : row.items).map((c, i) =>
            row.kind === 'top10'
              ? <TopTile key={c.videoId} card={c} index={i} onOpen={onTile} hover={hover} />
              : <Tile key={c.videoId} card={c} onOpen={onTile} hover={hover} />,
          )}
        </div>
        <button type="button" className="arrow r" aria-label="다음으로 스크롤" onClick={() => scroll(1)}>›</button>
      </div>
      {preview && <PreviewCard card={preview.card} anchor={preview.anchor} />}
    </section>
  )
}
