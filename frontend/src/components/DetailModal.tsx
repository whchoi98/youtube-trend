import { useEffect, useRef, useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { ApiError, fetchJson } from '../api'
import type { HistoryPoint, HomeCard } from '../types'
import { formatCount, formatTsKst, youtubeUrl } from '../format'
import { seriesAccent } from '../chartColors'
import { Modal } from './Modal'

type Loadable<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: T }

const TOOLTIP_STYLE = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
}

/** 타일 클릭 상세 — 영상 시계열(순위/조회수) 차트와 YouTube 이동 버튼.
 *  시계열은 전체 Top30 진입 영상만 기록되므로 빈 결과는 정상 상태다. */
export function DetailModal({ card, onClose }: { card: HomeCard; onClose: () => void }) {
  const [history, setHistory] = useState<Loadable<HistoryPoint[]>>({ status: 'loading' })
  const [scale, setScale] = useState<'linear' | 'log'>('linear')
  // 모달이 열린 채 다른 타일로 교체될 수 있다 — 늦은 응답은 세대 가드로 폐기
  const seqRef = useRef(0)

  useEffect(() => {
    const seq = ++seqRef.current
    setHistory({ status: 'loading' })
    fetchJson<{ videoId: string; points: HistoryPoint[] }>(
      `/api/videos/${encodeURIComponent(card.videoId)}/history?hours=168`,
    )
      .then((res) => {
        if (seq !== seqRef.current) return
        setHistory({ status: 'ready', data: res.points })
      })
      .catch((err: unknown) => {
        if (seq !== seqRef.current) return
        setHistory({
          status: 'error',
          message: err instanceof ApiError ? (err.body.error ?? '시계열을 불러오지 못했습니다') : '시계열을 불러오지 못했습니다',
        })
      })
  }, [card.videoId])

  const lineColor = seriesAccent()

  return (
    <Modal onClose={onClose} label="영상 상세">
      <div className="detail">
        <h3 className="detail-title">{card.title}</h3>
        <p className="muted">
          {card.channel} · {card.category} · 조회 {formatCount(card.views)} · 좋아요 {formatCount(card.likes)}
        </p>

        {history.status === 'loading' && <p className="muted">시계열 불러오는 중…</p>}
        {history.status === 'error' && <p className="muted">{history.message}</p>}
        {history.status === 'ready' && history.data.length === 0 && (
          <p className="muted">이 영상의 시계열 기록이 아직 없습니다 (전체 Top30 진입 영상만 기록됩니다)</p>
        )}

        {history.status === 'ready' && history.data.length > 0 && (
          <>
            <div className="detail-chart">
              <h4>순위 추이</h4>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={history.data}>
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
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={history.data}>
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
        )}

        <a className="go" href={youtubeUrl(card.videoId)} target="_blank" rel="noopener noreferrer">
          ▶ YouTube에서 보기
        </a>
      </div>
    </Modal>
  )
}
