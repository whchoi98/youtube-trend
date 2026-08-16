import { useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { HistoryPoint } from '../types'
import { formatCount, formatTsKst } from '../format'
import { seriesAccent } from '../chartColors'

const TOOLTIP_STYLE = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
}

/** 영상 시계열 차트 쌍(순위 + 조회수, 로그/선형 토글) — 상세 모달과
 *  영상 시계열 패널이 공유한다. */
export function HistoryCharts({ points, height = 160, maxRank = 30 }: {
  points: HistoryPoint[]
  height?: number
  maxRank?: number
}) {
  const [scale, setScale] = useState<'linear' | 'log'>('linear')
  const lineColor = seriesAccent()

  return (
    <>
      <div className="detail-chart">
        <h4>순위 추이</h4>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="ts" tickFormatter={formatTsKst} stroke="var(--text-muted)" minTickGap={24} />
            <YAxis reversed domain={[1, maxRank]} allowDecimals={false} stroke="var(--text-muted)" />
            <Tooltip
              labelFormatter={(label) => formatTsKst(String(label))}
              formatter={(value) => [`${value}위`, '순위']}
              contentStyle={TOOLTIP_STYLE}
            />
            <Line type="monotone" dataKey="rank" stroke={lineColor} dot={false} connectNulls={false} />
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
          <LineChart data={points}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="ts" tickFormatter={formatTsKst} stroke="var(--text-muted)" minTickGap={24} />
            <YAxis
              scale={scale}
              domain={scale === 'log' ? [1, 'auto'] : [0, 'auto']}
              allowDataOverflow={scale === 'log'}
              stroke="var(--text-muted)"
              tickFormatter={(v) => formatCount(Number(v))}
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
    </>
  )
}
