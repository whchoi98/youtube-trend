import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, fetchJson } from '../api'
import type { HistoryPoint, HomeData, HomeRow, Loadable } from '../types'
import { HistoryCharts } from './HistoryCharts'
import { musicUrl } from '../format'

function errMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.body.error ?? err.message : fallback
}

/** YouTube Music 시계열 패널 — 차트와 곡을 골라 시간별 순위/조회수 추이를
 *  본다. 순위 추이는 차트 스냅샷에서 파생되며, 차트 밖 시각은 끊긴 선으로
 *  나타난다(null — 실측값과 혼용하지 않음). */
export function ChartSeriesPanel() {
  const [charts, setCharts] = useState<Loadable<HomeRow[]>>({ status: 'loading' })
  const [chartId, setChartId] = useState('')
  const [videoId, setVideoId] = useState('')
  const [history, setHistory] = useState<Loadable<HistoryPoint[]>>({ status: 'loading' })
  const chartsSeqRef = useRef(0)
  const histSeqRef = useRef(0)

  const loadCharts = useCallback(() => {
    const seq = ++chartsSeqRef.current
    setCharts({ status: 'loading' })
    fetchJson<HomeData>('/api/home')
      .then((d) => {
        if (seq !== chartsSeqRef.current) return
        const rows = d.rows.filter((r) => r.kind === 'chart')
        setCharts({ status: 'ready', data: rows })
        setChartId((prev) => prev || rows[0]?.chartId || '')
      })
      .catch((err: unknown) => {
        if (seq !== chartsSeqRef.current) return
        setCharts({ status: 'error', message: errMessage(err, '차트 목록을 불러오지 못했습니다') })
      })
  }, [])

  useEffect(() => {
    loadCharts()
    return () => {
      chartsSeqRef.current += 1
      histSeqRef.current += 1
    }
  }, [loadCharts])

  const chartRows = charts.status === 'ready' ? charts.data : []
  const currentChart = chartRows.find((r) => r.chartId === chartId) ?? null

  // 차트 전환 시 선택 곡이 그 차트에 없으면 1위 곡으로 재설정
  useEffect(() => {
    if (!currentChart) return
    setVideoId((prev) =>
      currentChart.items.some((c) => c.videoId === prev)
        ? prev
        : currentChart.items[0]?.videoId ?? '')
  }, [currentChart])

  const loadHistory = useCallback((cid: string, vid: string) => {
    const seq = ++histSeqRef.current
    setHistory({ status: 'loading' })
    fetchJson<{ points: HistoryPoint[] }>(
      `/api/charts/${encodeURIComponent(cid)}/videos/${encodeURIComponent(vid)}/history?hours=72`,
    )
      .then((res) => {
        if (seq !== histSeqRef.current) return
        setHistory({ status: 'ready', data: res.points })
      })
      .catch((err: unknown) => {
        if (seq !== histSeqRef.current) return
        setHistory({ status: 'error', message: errMessage(err, '차트 추이를 불러오지 못했습니다') })
      })
  }, [])

  useEffect(() => {
    if (chartId && videoId) loadHistory(chartId, videoId)
  }, [chartId, videoId, loadHistory])

  if (charts.status === 'loading') return <p className="muted">차트 목록 불러오는 중…</p>
  if (charts.status === 'error') {
    return (
      <div className="state-message">
        <p>{charts.message}</p>
        <button type="button" onClick={loadCharts}>다시 시도</button>
      </div>
    )
  }
  if (chartRows.length === 0) {
    return <p className="muted">아직 수집된 차트가 없습니다 — 다음 정시 수집 후 표시됩니다</p>
  }

  return (
    <>
      <div className="video-controls">
        <select value={chartId} onChange={(e) => setChartId(e.target.value)} aria-label="차트 선택">
          {chartRows.map((r) => (
            <option key={r.chartId} value={r.chartId}>{r.title}</option>
          ))}
        </select>
        <select value={videoId} onChange={(e) => setVideoId(e.target.value)} aria-label="곡 선택">
          {(currentChart?.items ?? []).map((c) => (
            <option key={c.videoId} value={c.videoId}>
              {c.rank}. {c.title} — {c.channel}
            </option>
          ))}
        </select>
        {videoId && (
          <a className="music-link" href={musicUrl(videoId)} target="_blank" rel="noopener noreferrer">
            YouTube Music에서 듣기
          </a>
        )}
      </div>

      {history.status === 'loading' && <p className="muted">추이 불러오는 중…</p>}
      {history.status === 'error' && (
        <div className="state-message">
          <p>{history.message}</p>
          <button type="button" onClick={() => loadHistory(chartId, videoId)}>다시 시도</button>
        </div>
      )}
      {history.status === 'ready' && history.data.length === 0 && (
        <p className="muted">이 차트의 시계열 기록이 아직 없습니다</p>
      )}
      {history.status === 'ready' && history.data.length > 0 && (
        <HistoryCharts points={history.data} height={220} maxRank={20} />
      )}
    </>
  )
}
