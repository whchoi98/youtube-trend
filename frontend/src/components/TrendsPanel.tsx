import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Legend,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { ApiError, fetchJson } from '../api'
import type { Category, TrendBucket } from '../types'
import { formatTsKst } from '../format'
import { categoricalPalette, enteredColor, exitedColor } from '../chartColors'
import { PeriodToggle } from './PeriodToggle'

// 점유율 패널 전용 기간 — 기존 기본 48시간을 유지하면서 일주일/한 달을 더한다
const TREND_PERIODS = [
  { hours: 48, label: '48시간' },
  { hours: 168, label: '일주일' },
  { hours: 720, label: '한 달' },
] as const

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

type ShareRow = { ts: string; entered: number | null; exited: number | null; [catId: string]: number | string | null }

/** 카테고리 점유율 스택 차트 + 진입/이탈 막대 — 하단 패널용. */
export function TrendsPanel() {
  const [categories, setCategories] = useState<Loadable<Category[]>>({ status: 'loading' })
  const [trend, setTrend] = useState<Loadable<TrendBucket[]>>({ status: 'loading' })
  const [hours, setHours] = useState<number>(48)
  const [stepHours, setStepHours] = useState(1)
  // 재시도 연타·언마운트 후 늦은 응답을 폐기하는 세대 가드 — 두 로더가 동시에
  // 비행하므로 카운터를 공유하면 서로를 폐기한다. 로더별 독립 ref를 쓴다.
  const catSeqRef = useRef(0)
  const trendSeqRef = useRef(0)

  const loadCategories = useCallback(() => {
    const seq = ++catSeqRef.current
    setCategories({ status: 'loading' })
    fetchJson<Category[]>('/api/categories')
      .then((data) => {
        if (seq !== catSeqRef.current) return
        setCategories({ status: 'ready', data })
      })
      .catch((err: unknown) => {
        if (seq !== catSeqRef.current) return
        setCategories({ status: 'error', message: errMessage(err, '분야 목록을 불러오지 못했습니다') })
      })
  }, [])

  const loadTrend = useCallback(() => {
    const seq = ++trendSeqRef.current
    setTrend({ status: 'loading' })
    fetchJson<{ hours: number; stepHours?: number; series: TrendBucket[] }>(
      `/api/trends/categories?hours=${hours}`,
    )
      .then((res) => {
        if (seq !== trendSeqRef.current) return
        setStepHours(res.stepHours ?? 1)
        setTrend({ status: 'ready', data: res.series })
      })
      .catch((err: unknown) => {
        if (seq !== trendSeqRef.current) return
        setTrend({ status: 'error', message: errMessage(err, '추이 데이터를 불러오지 못했습니다') })
      })
  }, [hours])

  // 카테고리 목록은 마운트 시 1회만 — loadTrend는 hours에 의존하므로 effect를
  // 합치면 기간 토글마다 불변 목록까지 재요청되고 패널 전체가 로딩으로 플래시한다
  useEffect(() => {
    loadCategories()
    return () => {
      catSeqRef.current += 1 // 언마운트 후 도착하는 응답 무효화
    }
  }, [loadCategories])

  useEffect(() => {
    loadTrend()
    return () => {
      trendSeqRef.current += 1 // 언마운트·기간 교체 후 도착하는 응답 무효화
    }
  }, [loadTrend])

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
    // 백엔드 shares는 그 시간대에 실제로 등장한 catId만 포함한다 — 한 시간이라도 순위권
    // 밖으로 빠진 카테고리는 그 버킷에서 undefined가 되어 스택 AreaChart가 끊긴다.
    // 전체 series에서 등장한 catId(ids)를 기준으로 누락분을 0으로 채운다.
    const data: ShareRow[] = trend.data.map((b) => ({
      ts: b.ts,
      entered: b.entered,
      exited: b.exited,
      ...Object.fromEntries(ids.map((id) => [id, b.shares[id] ?? 0])),
    }))
    return { catIds: ids, rows: data }
  }, [trend, categories])

  const palette = categoricalPalette()
  const isLoading = categories.status === 'loading' || trend.status === 'loading'
  const errorMsg = trend.status === 'error' ? trend.message : categories.status === 'error' ? categories.message : null

  // 기간 토글은 로딩·오류 중에도 유지한다 — 긴 기간을 눌렀다가 되돌릴 수 있어야 한다
  const controls = (
    <div className="video-controls">
      <PeriodToggle value={hours} onChange={setHours} periods={TREND_PERIODS} />
      {stepHours > 1 && trend.status === 'ready' && (
        <span className="coverage-note">{stepHours}시간 간격 샘플</span>
      )}
    </div>
  )

  if (isLoading) return <>{controls}<p className="muted">불러오는 중…</p></>

  if (errorMsg) {
    return (
      <>
        {controls}
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
      </>
    )
  }

  if (rows.length === 0) return <>{controls}<p className="muted">데이터 수집 중…</p></>

  return (
    <>
      {controls}
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
        <h4>진입/이탈</h4>
        <ResponsiveContainer width="100%" height={180}>
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
  )
}
