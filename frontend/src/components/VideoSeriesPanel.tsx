import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, fetchJson } from '../api'
import type { Card, Loadable } from '../types'
import { useVideoHistory } from '../useVideoHistory'
import { HistoryCharts } from './HistoryCharts'
import { PeriodToggle } from './PeriodToggle'

function errMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.body.error ?? err.message : fallback
}

/** 영상 시계열 패널 — 구 '추이 분석' 탭의 상단 선택 방식 복원: 전체 Top30에서
 *  영상을 골라 최근 7일 순위/조회수 추이를 상세히 본다. */
export function VideoSeriesPanel() {
  const [videos, setVideos] = useState<Loadable<Card[]>>({ status: 'loading' })
  const [selectedId, setSelectedId] = useState('')
  const [hours, setHours] = useState(168)
  const videosSeqRef = useRef(0)
  const { history, retry } = useVideoHistory(selectedId, hours)

  const loadVideos = useCallback(() => {
    const seq = ++videosSeqRef.current
    setVideos({ status: 'loading' })
    fetchJson<Card[]>('/api/trending?scope=all')
      .then((cards) => {
        if (seq !== videosSeqRef.current) return
        setVideos({ status: 'ready', data: cards })
        setSelectedId((prev) => prev || cards[0]?.videoId || '')
      })
      .catch((err: unknown) => {
        if (seq !== videosSeqRef.current) return
        setVideos({ status: 'error', message: errMessage(err, '영상 목록을 불러오지 못했습니다') })
      })
  }, [])

  useEffect(() => {
    loadVideos()
    return () => {
      videosSeqRef.current += 1 // 언마운트(패널 remount 새로고침) 후 응답 무효화
    }
  }, [loadVideos])

  return (
    <>
      {videos.status === 'loading' && <p className="muted">영상 목록 불러오는 중…</p>}

      {videos.status === 'error' && (
        <div className="state-message">
          <p>{videos.message}</p>
          <button type="button" onClick={loadVideos}>다시 시도</button>
        </div>
      )}

      {videos.status === 'ready' && videos.data.length === 0 && (
        <p className="muted">표시할 목록이 아직 없습니다</p>
      )}

      {videos.status === 'ready' && videos.data.length > 0 && (
        <div className="video-controls">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            aria-label="영상 선택"
          >
            {videos.data.map((c) => (
              <option key={c.videoId} value={c.videoId}>
                {c.rank}. {c.title} — {c.channel}
              </option>
            ))}
          </select>
          <PeriodToggle value={hours} onChange={setHours} />
        </div>
      )}

      {selectedId && history.status === 'loading' && <p className="muted">시계열 불러오는 중…</p>}

      {selectedId && history.status === 'error' && (
        <div className="state-message">
          <p>{history.message}</p>
          <button type="button" onClick={retry}>다시 시도</button>
        </div>
      )}

      {selectedId && history.status === 'ready' && history.data.length === 0 && (
        <p className="muted">이 영상의 시계열 기록이 아직 없습니다</p>
      )}

      {selectedId && history.status === 'ready' && history.data.length > 0 && (
        <HistoryCharts
          points={history.data}
          height={220}
          windowHours={hours}
          coverageNote="급상승 목록에 오른 동안에만 시간별로 적재됩니다"
        />
      )}
    </>
  )
}
