import type { HomeCard } from '../types'
import { useVideoHistory } from '../useVideoHistory'
import { HistoryCharts } from './HistoryCharts'

/** 히어로에서 선택된 콘텐츠의 추이 — 히어로 바로 아래 패널로 표시한다. */
export function SelectedTrend({ card }: { card: HomeCard }) {
  const { history, retry } = useVideoHistory(card.videoId)

  if (history.status === 'loading') return <p className="muted">시계열 불러오는 중…</p>
  if (history.status === 'error') {
    return (
      <div className="state-message">
        <p>{history.message}</p>
        <button type="button" onClick={retry}>다시 시도</button>
      </div>
    )
  }
  if (history.data.length === 0) {
    return <p className="muted">이 영상의 시계열 기록이 아직 없습니다 (전체 Top30 진입 영상만 기록됩니다)</p>
  }
  return <HistoryCharts points={history.data} height={200} />
}
