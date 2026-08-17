import { useMemo, useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { HistoryPoint } from '../types'
import { bucketMs, formatCount, formatMsKst, formatTsKst } from '../format'
import { seriesAccent } from '../chartColors'

const TOOLTIP_STYLE = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
}

const HOUR_MS = 3_600_000
const X_TICK_COUNT = 6

/** 영상 시계열 차트 쌍(순위 + 조회수, 로그/선형 토글) — 상세 모달과
 *  영상/차트 시계열 패널이 공유한다.
 *
 *  windowHours를 주면 X축이 데이터 범위가 아니라 [지금-기간, 지금]에 고정된다.
 *  시계열 포인트는 급상승/차트에 오른 동안에만 적재되므로 데이터가 기간보다
 *  짧은 게 보통인데, 자동 맞춤 축은 기간을 바꿔도 차트가 그대로 보이게 만든다
 *  (기간 토글 무반응처럼 보이는 원인). 고정 도메인 + 적재 구간 안내로 해소한다. */
export function HistoryCharts({ points, height = 160, maxRank = 30, windowHours, coverageNote }: {
  points: HistoryPoint[]
  height?: number
  maxRank?: number
  /** X축을 고정할 조회 기간(시간). 없으면 기존처럼 데이터 범위에 맞춘다. */
  windowHours?: number
  /** 적재 구간이 기간보다 짧을 때 덧붙일 설명(패널별 적재 조건). */
  coverageNote?: string
}) {
  const [scale, setScale] = useState<'linear' | 'log'>('linear')
  const lineColor = seriesAccent()

  const windowed = useMemo(() => {
    if (!windowHours) return null
    const until = Date.now()
    const since = until - windowHours * HOUR_MS
    const real = points
      .map((p) => ({ ts: p.ts, rank: p.rank, views: p.views as number | null, t: bucketMs(p.ts) }))
      .filter((p) => Number.isFinite(p.t))
    // 결측 버킷은 null 포인트가 아니라 '부재'라 숫자 시간축에서 긴 직선으로
    // 보간된다 — 2시간 초과 공백(수집 폴백 허용치)에 null 브레이커를 넣어
    // 급상승 이탈~재진입 구간이 연속 추이처럼 보이지 않게 한다.
    const data: typeof real = []
    for (const p of real) {
      const prev = data[data.length - 1]
      if (prev && prev.rank !== null && p.t - prev.t > 2 * HOUR_MS) {
        data.push({ ts: '', rank: null, views: null, t: prev.t + HOUR_MS })
      }
      data.push(p)
    }
    const ticks = Array.from(
      { length: X_TICK_COUNT + 1 },
      (_, i) => since + (i * (until - since)) / X_TICK_COUNT,
    )
    // 적재량은 외연(첫~마지막 간격)이 아니라 실제 포인트 수다 — 갭이 있는
    // 재진입 시계열에서 외연 기준은 안내를 숨기거나 과대 표기한다
    return {
      since, until, data, ticks,
      count: real.length,
      first: real[0]?.t, last: real[real.length - 1]?.t,
      coarse: windowHours > 48,
    }
  }, [points, windowHours])

  const xAxis = windowed
    ? {
        dataKey: 't',
        type: 'number' as const,
        domain: [windowed.since, windowed.until] as [number, number],
        ticks: windowed.ticks as unknown as number[],
        tickFormatter: (v: number) => formatMsKst(Number(v), windowed.coarse),
      }
    : {
        dataKey: 'ts',
        tickFormatter: formatTsKst,
      }
  const labelFormatter = (label: unknown) =>
    windowed ? formatMsKst(Number(label)) : formatTsKst(String(label))
  // 브레이커 포인트(views: null)는 HistoryPoint보다 넓다 — recharts에는 무해
  const chartData = (windowed ? windowed.data : points) as HistoryPoint[]
  // 포인트가 기간 대비 듬성하면(다운샘플·짧은 적재) 선만으로는 안 보일 수 있어 점을 켠다
  const showDots = windowed !== null && windowed.data.length <= 48

  return (
    <>
      <div className="detail-chart">
        <h4>순위 추이</h4>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis {...xAxis} stroke="var(--text-muted)" minTickGap={24} />
            <YAxis reversed domain={[1, maxRank]} allowDecimals={false} stroke="var(--text-muted)" />
            <Tooltip
              labelFormatter={labelFormatter}
              formatter={(value) => [`${value}위`, '순위']}
              contentStyle={TOOLTIP_STYLE}
            />
            <Line type="monotone" dataKey="rank" stroke={lineColor} dot={showDots ? { r: 2 } : false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="detail-chart">
        <div className="detail-chart-head">
          <h4>조회수 추이</h4>
          <button
            type="button"
            className={scale === 'log' ? 'toggle active' : 'toggle'}
            aria-pressed={scale === 'log'}
            onClick={() => setScale((s) => (s === 'log' ? 'linear' : 'log'))}
          >
            {scale === 'log' ? '로그' : '선형'}
          </button>
        </div>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis {...xAxis} stroke="var(--text-muted)" minTickGap={24} />
            <YAxis
              scale={scale}
              domain={scale === 'log' ? [1, 'auto'] : [0, 'auto']}
              allowDataOverflow={scale === 'log'}
              stroke="var(--text-muted)"
              tickFormatter={(v) => formatCount(Number(v))}
            />
            <Tooltip
              labelFormatter={labelFormatter}
              formatter={(value) => [formatCount(Number(value)), '조회수']}
              contentStyle={TOOLTIP_STYLE}
            />
            <Line type="monotone" dataKey="views" stroke={lineColor} dot={showDots ? { r: 2 } : false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {windowed && windowed.count > 0 && windowed.count < windowHours! && (
        <p className="coverage-note">
          적재 {windowed.count}시간분 ({formatMsKst(windowed.first!)} ~ {formatMsKst(windowed.last!)})
          {coverageNote ? ` — ${coverageNote}` : ''}
        </p>
      )}
    </>
  )
}
