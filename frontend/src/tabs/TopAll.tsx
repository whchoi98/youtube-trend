import { useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError, fetchJson } from '../api'
import type { Card as CardData } from '../types'
import { CardGrid, CardSkeletonGrid } from '../components/CardGrid'
import { formatCount } from '../format'

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; cards: CardData[] }

interface Stats {
  totalViews: number
  channelCount: number
  topCategory: string
}

function computeStats(cards: CardData[]): Stats {
  const totalViews = cards.reduce((sum, c) => sum + c.views, 0)
  const channelCount = new Set(cards.map((c) => c.channel)).size

  const categoryCounts = new Map<string, number>()
  for (const c of cards) {
    categoryCounts.set(c.category, (categoryCounts.get(c.category) ?? 0) + 1)
  }
  let topCategory = '-'
  let topCount = 0
  for (const [name, count] of categoryCounts) {
    if (count > topCount) {
      topCategory = name
      topCount = count
    }
  }
  return { totalViews, channelCount, topCategory }
}

export function TopAll() {
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  const load = useCallback(() => {
    setState({ status: 'loading' })
    fetchJson<CardData[]>('/api/trending?scope=all')
      .then((cards) => setState({ status: 'ready', cards }))
      .catch((err: unknown) => {
        const message = err instanceof ApiError
          ? err.body.error ?? err.message
          : '목록을 불러오지 못했습니다'
        setState({ status: 'error', message })
      })
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const stats = useMemo(
    () => (state.status === 'ready' ? computeStats(state.cards) : null),
    [state],
  )

  if (state.status === 'loading') {
    return (
      <section>
        <StatTiles stats={null} />
        <CardSkeletonGrid count={8} />
      </section>
    )
  }

  if (state.status === 'error') {
    return (
      <section className="state-message">
        <p>{state.message}</p>
        <button type="button" onClick={load}>다시 시도</button>
      </section>
    )
  }

  return (
    <section>
      <StatTiles stats={stats} />
      <CardGrid cards={state.cards} />
    </section>
  )
}

function StatTiles({ stats }: { stats: Stats | null }) {
  return (
    <div className="stat-tiles">
      <div className="stat-tile">
        <span className="stat-label">합산 조회수</span>
        <span className="stat-value">{stats ? formatCount(stats.totalViews) : '-'}</span>
      </div>
      <div className="stat-tile">
        <span className="stat-label">채널 수</span>
        <span className="stat-value">{stats ? stats.channelCount : '-'}</span>
      </div>
      <div className="stat-tile">
        <span className="stat-label">최다 카테고리</span>
        <span className="stat-value">{stats ? stats.topCategory : '-'}</span>
      </div>
    </div>
  )
}
