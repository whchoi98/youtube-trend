import { useState } from 'react'
import type { HomeHero } from '../types'
import { formatCount, youtubeUrl } from '../format'

/** 홈 최상단 히어로 — 전체 1위 영상의 maxres 썸네일을 배경으로 깐다.
 *  maxres가 없는 영상(404)은 onError로 저장된 일반 썸네일로 폴백한다. */
export function Hero({ hero, onQuiz }: { hero: HomeHero | null; onQuiz: () => void }) {
  // 실패를 videoId 단위로 기억한다 — boolean이면 1위가 교체돼도 실패 상태가
  // 남아 새 히어로의 maxres 배경까지 비활성화된다
  const [failedId, setFailedId] = useState<string | null>(null)
  if (!hero) return null

  const isNew = hero.baseline !== null && hero.prevRank === null
  const bgFailed = failedId === hero.videoId
  const bg = bgFailed || !hero.heroThumbnail ? hero.thumbnail : hero.heroThumbnail
  const vph = hero.viewsPerHour !== null && hero.viewsPerHour > 0
    ? ` (+${formatCount(hero.viewsPerHour)}/시)` : ''

  return (
    <div className="hero">
      {bg && (
        <img
          className="hero-bg"
          src={bg}
          alt=""
          aria-hidden="true"
          onError={() => setFailedId(hero.videoId)}
        />
      )}
      <div className="hero-info">
        <div className="hero-rank">
          지금 한국 1위
          {hero.tenureHours > 1 ? ` · ${hero.tenureHours}시간째 차트인` : ''}
          {isNew && <span className="hero-new">오늘 첫 진입</span>}
        </div>
        <h1 className="hero-title">{hero.title}</h1>
        <div className="hero-meta">
          {hero.channel} · 조회 {formatCount(hero.views)}{vph} · 좋아요 {formatCount(hero.likes)}
        </div>
        <div className="hero-actions">
          <a className="btn-play" href={youtubeUrl(hero.videoId)} target="_blank" rel="noopener noreferrer">
            ▶ 보러가기
          </a>
          <button type="button" className="btn-quiz" onClick={onQuiz}>
            🧭 내 취향 찾기
          </button>
        </div>
      </div>
    </div>
  )
}
