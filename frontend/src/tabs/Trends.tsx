import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { ApiError, fetchJson } from '../api'
import type { Card as CardData, Category, HistoryPoint, TrendBucket } from '../types'
import { formatCount, formatTsKst } from '../format'
import { categoricalPalette, enteredColor, exitedColor, seriesAccent } from '../chartColors'
import { BriefPanel } from '../components/BriefPanel'

type Loadable<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: T }

function errMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.body.error ?? err.message : fallback
}

const TOOLTIP_STYLE = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
}

export function Trends() {
  return (
    <section className="trends-tab">
      <VideoSeriesSection />
      <CategoryShareSection />
      <div className="trend-section">
        <h2>브리핑 / 리포트</h2>
        <BriefPanel />
      </div>
    </section>
  )
}

function VideoSeriesSection() {
  const [videos, setVideos] = useState<Loadable<CardData[]>>({ status: 'loading' })
  const [selectedId, setSelectedId] = useState('')
  const [history, setHistory] = useState<Loadable<HistoryPoint[]>>({ status: 'loading' })
  const [scale, setScale] = useState<'linear' | 'log'>('linear')

  const loadVideos = useCallback(() => {
    setVideos({ status: 'loading' })
    fetchJson<CardData[]>('/api/trending?scope=all')
      .then((cards) => {
        setVideos({ status: 'ready', data: cards })
        setSelectedId((prev) => prev || cards[0]?.videoId || '')
      })
      .catch((err: unknown) => setVideos({ status: 'error', message: errMessage(err, '영상 목록을 불러오지 못했습니다') }))
  }, [])

  useEffect(() => {
    loadVideos()
  }, [loadVideos])

  const loadHistory = useCallback((videoId: string) => {
    setHistory({ status: 'loading' })
    fetchJson<{ videoId: string; points: HistoryPoint[] }>(`/api/videos/${videoId}/history?hours=168`)
      .then((res) => setHistory({ status: 'ready', data: res.points }))
      .catch((err: unknown) => setHistory({ status: 'error', message: errMessage(err, '시계열을 불러오지 못했습니다') }))
  }, [])

  useEffect(() => {
    if (selectedId) loadHistory(selectedId)
  }, [selectedId, loadHistory])

  const lineColor = seriesAccent()

  const chartData = useMemo(
    () => (history.status === 'ready' ? history.data : []),
    [history],
  )

  return (
    <div className="trend-section">
      <h2>영상 시계열</h2>

      {videos.status === 'loading' && <p className="hint-text">영상 목록 불러오는 중…</p>}

      {videos.status === 'error' && (
        <div className="state-message">
          <p>{videos.message}</p>
          <button type="button" onClick={loadVideos}>다시 시도</button>
        </div>
      )}

      {videos.status === 'ready' && (
        <div className="trend-controls">
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)} aria-label="영상 선택">
            {videos.data.map((c) => (
              <option key={c.videoId} value={c.videoId}>
                {c.rank}. {c.title} — {c.channel}
              </option>
            ))}
          </select>
          <button
            type="button"
            className={scale === 'log' ? 'toggle active' : 'toggle'}
            aria-pressed={scale === 'log'}
            onClick={() => setScale((s) => (s === 'log' ? 'linear' : 'log'))}
          >
            조회수 {scale === 'log' ? '로그' : '선형'} 스케일
          </button>
        </div>
      )}

      {history.status === 'loading' && <p className="hint-text">시계열 불러오는 중…</p>}

      {history.status === 'error' && (
        <div className="state-message">
          <p>{history.message}</p>
          <button type="button" onClick={() => selectedId && loadHistory(selectedId)}>다시 시도</button>
        </div>
      )}

      {history.status === 'ready' && (
        <div className="chart-pair">
          <div className="chart-box">
            <h3>순위 추이</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="ts" tickFormatter={formatTsKst} stroke="var(--text-muted)" minTickGap={24} />
                <YAxis reversed domain={[1, 30]} allowDecimals={false} stroke="var(--text-muted)" />
                <Tooltip
                  labelFormatter={(label) => formatTsKst(String(label))}
                  formatter={(value) => [`${value}위`, '순위']}
                  contentStyle={TOOLTIP_STYLE}
                />
                <Line type="monotone" dataKey="rank" stroke={lineColor} dot={false} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-box">
            <h3>조회수 추이</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="ts" tickFormatter={formatTsKst} stroke="var(--text-muted)" minTickGap={24} />
                <YAxis
                  scale={scale}
                  domain={scale === 'log' ? [1, 'auto'] : [0, 'auto']}
                  allowDataOverflow={scale === 'log'}
                  stroke="var(--text-muted)"
                />
                <Tooltip
                  labelFormatter={(label) => formatTsKst(String(label))}
                  formatter={(value) => [formatCount(Number(value)), '조회수']}
                  contentStyle={TOOLTIP_STYLE}
                />
                <Line type="monotone" dataKey="views" stroke={lineColor} dot={false} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}

type ShareRow = { ts: string; entered: number; exited: number; [catId: string]: number | string }

function CategoryShareSection() {
  const [categories, setCategories] = useState<Loadable<Category[]>>({ status: 'loading' })
  const [trend, setTrend] = useState<Loadable<TrendBucket[]>>({ status: 'loading' })

  const loadCategories = useCallback(() => {
    setCategories({ status: 'loading' })
    fetchJson<Category[]>('/api/categories')
      .then((data) => setCategories({ status: 'ready', data }))
      .catch((err: unknown) => setCategories({ status: 'error', message: errMessage(err, '분야 목록을 불러오지 못했습니다') }))
  }, [])

  const loadTrend = useCallback(() => {
    setTrend({ status: 'loading' })
    fetchJson<{ hours: number; series: TrendBucket[] }>('/api/trends/categories?hours=48')
      .then((res) => setTrend({ status: 'ready', data: res.series }))
      .catch((err: unknown) => setTrend({ status: 'error', message: errMessage(err, '추이 데이터를 불러오지 못했습니다') }))
  }, [])

  useEffect(() => {
    loadCategories()
    loadTrend()
  }, [loadCategories, loadTrend])

  const nameOf = useMemo(() => {
    const map = new Map<string, string>()
    if (categories.status === 'ready') {
      for (const c of categories.data) map.set(c.id, c.name)
    }
    return (id: string) => map.get(id) ?? (id === '' ? '기타' : id)
  }, [categories])

  const { catIds, rows } = useMemo(() => {
    if (trend.status !== 'ready') return { catIds: [] as string[], rows: [] as ShareRow[] }
    const present = new Set<string>()
    for (const b of trend.data) for (const id of Object.keys(b.shares)) present.add(id)
    const known = categories.status === 'ready' ? categories.data.map((c) => c.id) : []
    const orderedKnown = known.filter((id) => present.has(id))
    const extra = Array.from(present).filter((id) => !known.includes(id)).sort()
    const ids = [...orderedKnown, ...extra]
    const data: ShareRow[] = trend.data.map((b) => ({ ts: b.ts, entered: b.entered, exited: b.exited, ...b.shares }))
    return { catIds: ids, rows: data }
  }, [trend, categories])

  const palette = categoricalPalette()
  const isLoading = categories.status === 'loading' || trend.status === 'loading'
  const errorMsg = trend.status === 'error' ? trend.message : categories.status === 'error' ? categories.message : null

  return (
    <div className="trend-section">
      <h2>카테고리 점유율</h2>

      {isLoading && <p className="hint-text">불러오는 중…</p>}

      {errorMsg && (
        <div className="state-message">
          <p>{errorMsg}</p>
          <button
            type="button"
            onClick={() => {
              loadCategories()
              loadTrend()
            }}
          >
            다시 시도
          </button>
        </div>
      )}

      {!isLoading && !errorMsg && (
        <>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="ts" tickFormatter={formatTsKst} stroke="var(--text-muted)" minTickGap={24} />
                <YAxis allowDecimals={false} stroke="var(--text-muted)" />
                <Tooltip labelFormatter={(label) => formatTsKst(String(label))} contentStyle={TOOLTIP_STYLE} />
                {/* 기본 itemSorter="value"는 이름 문자열로 재정렬한다 — 카테고리 고정 순서(색상 슬롯과 동일 순서)를 유지하려면 끈다. */}
                <Legend itemSorter={null} />
                {catIds.map((id, i) => (
                  <Area
                    key={id || '__uncategorized'}
                    type="monotone"
                    dataKey={id}
                    stackId="cat"
                    name={nameOf(id)}
                    stroke={palette[i % palette.length]}
                    fill={palette[i % palette.length]}
                    fillOpacity={0.75}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-box">
            <h3>진입/이탈</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="ts" tickFormatter={formatTsKst} stroke="var(--text-muted)" minTickGap={24} />
                <YAxis allowDecimals={false} stroke="var(--text-muted)" />
                <Tooltip labelFormatter={(label) => formatTsKst(String(label))} contentStyle={TOOLTIP_STYLE} />
                <Legend itemSorter={null} />
                <Bar dataKey="entered" name="진입" fill={enteredColor()} />
                <Bar dataKey="exited" name="이탈" fill={exitedColor()} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
