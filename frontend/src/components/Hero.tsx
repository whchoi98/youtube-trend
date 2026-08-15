import { useState } from 'react'
import type { HomeCard, HomeHero } from '../types'
import { formatCount, youtubeUrl } from '../format'

function maxresUrl(videoId: string): string {
  return `https://i.ytimg.com/vi/${encodeURIComponent(videoId)}/maxresdefault.jpg`
}

/** 홈 최상단 히어로. 기본은 전체 1위 영상이고, 타일에서 콘텐츠를 선택하면
 *  넷플릭스 빌보드처럼 그 콘텐츠의 제목·카테고리·간단한 소개·링크로 바뀐다.
 *  maxres가 없는 영상(404)은 onError로 저장된 일반 썸네일로 폴백한다. */
export function Hero({ hero, selected, onQuiz, onClear }: {
  hero: HomeHero | null
  selected: HomeCard | null
  onQuiz: () => void
  onClear: () => void
}) {
  // 실패를 videoId 단위로 기억한다 — boolean이면 표시 대상이 교체돼도 실패
  // 상태가 남아 새 콘텐츠의 maxres 배경까지 비활성화된다
  const [failedId, setFailedId] = useState<string | null>(null)
  const card = selected ?? hero
  if (!card) return null

  const isNew = card.baseline !== null && card.prevRank === null
  const maxres = selected ? maxresUrl(selected.videoId) : hero?.heroThumbnail ?? ''
  const bg = failedId === card.videoId || !maxres ? card.thumbnail : maxres
  const vph = card.viewsPerHour !== null && card.viewsPerHour > 0
    ? ` (+${formatCount(card.viewsPerHour)}/시)` : ''

  return (
    <div className="hero">
      {bg && (
        <img
          className="hero-bg"
          src={bg}
          alt=""
          aria-hidden="true"
          onError={() => setFailedId(card.videoId)}
        />
      )}
      <div className="hero-info">
        <div className="hero-rank">
          {selected ? `급상승 ${card.rank}위` : (
            <>
              지금 한국 1위
              {hero && hero.tenureHours > 1 ? ` · ${hero.tenureHours}시간째 차트인` : ''}
            </>
          )}
          {card.category && <span className="hero-cat">{card.category}</span>}
          {isNew && <span className="hero-new">오늘 첫 진입</span>}
        </div>
        <h1 className="hero-title">{card.title}</h1>
        {card.description && <p className="hero-desc">{card.description}</p>}
        <div className="hero-meta">
          {card.channel} · 조회 {formatCount(card.views)}{vph} · 좋아요 {formatCount(card.likes)}
        </div>
        <div className="hero-actions">
          <a className="btn-play" href={youtubeUrl(card.videoId)} target="_blank" rel="noopener noreferrer">
            ▶ 보러가기
          </a>
          {selected ? (
            <button type="button" className="btn-quiz" onClick={onClear}>
              ✕ 1위 화면으로
            </button>
          ) : (
            <button type="button" className="btn-quiz" onClick={onQuiz}>
              🧭 내 취향 찾기
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
