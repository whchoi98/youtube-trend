import { useState } from 'react'
import type { ChannelStat } from '../types'
import { formatCount } from '../format'

function Avatar({ ch }: { ch: ChannelStat }) {
  const [failed, setFailed] = useState(false)
  if (failed || !ch.thumbnail) return <span className="chan-avatar-fallback" aria-hidden="true" />
  return <img src={ch.thumbnail} alt="" loading="lazy" onError={() => setFailed(true)} />
}

/** '지금 뜨는 채널' — 급상승 목록 기여 채널 랭킹(합산 조회수 기준).
 *  카드를 누르면 해당 채널의 YouTube 페이지가 열린다. */
export function ChannelStrip({ channels }: { channels: ChannelStat[] }) {
  return (
    <section className="row">
      <h2>
        지금 뜨는 채널
        <span className="hint">급상승 기여 · 합산 조회수 기준</span>
      </h2>
      <div className="strip-wrap">
        <div className="strip">
          {channels.map((ch) => (
            <a
              key={ch.channelId}
              className="chan-card"
              href={`https://www.youtube.com/channel/${encodeURIComponent(ch.channelId)}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <span className={ch.rank <= 3 ? 'tile-rank top3' : 'tile-rank'}>{ch.rank}</span>
              <Avatar ch={ch} />
              <span className="chan-name">{ch.name}</span>
              <span className="chan-meta">
                {ch.subscribers !== null ? `구독 ${formatCount(ch.subscribers)}` : '구독자 비공개'}
                {ch.totalViews !== null && ` · 총 ${formatCount(ch.totalViews)}회`}
              </span>
              <span className="chan-meta strong">
                급상승 {ch.trendingCount}편 · {formatCount(ch.trendingViews)}회
              </span>
            </a>
          ))}
        </div>
      </div>
    </section>
  )
}
