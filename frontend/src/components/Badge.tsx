import type { Card } from '../types'

export function DeltaBadge({ c }: { c: Card }) {
  if (c.baseline === null) return null
  if (c.prevRank === null) return <span className="badge new">NEW</span>
  if (c.delta === null || c.delta === 0) return <span className="badge same">-</span>
  return c.delta > 0
    ? <span className="badge up">{'↑'}{c.delta}</span>
    : <span className="badge down">{'↓'}{-c.delta}</span>
}

export function velocityText(v: number | null): string | null {
  if (v === null) return null
  const abs = Math.abs(v)
  const num = abs >= 10000 ? `${(abs / 10000).toFixed(1)}만` : `${abs}`
  return `${v > 0 ? '+' : v < 0 ? '-' : ''}${num}/시`  // ASCII 부호(글리프 커버리지)
}

/** 카테고리 배지 — 카드 하단에 분야명을 표시한다. */
export function CategoryBadge({ name }: { name: string }) {
  return <span className="badge category">{name}</span>
}
