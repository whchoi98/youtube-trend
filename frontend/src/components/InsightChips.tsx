/** 히어로 아래 인사이트 칩 — 백엔드가 계산한 한 줄 요약들(LLM 미사용). */
export function InsightChips({ items }: { items: string[] }) {
  if (items.length === 0) return null
  return (
    <div className="insights">
      {items.map((t) => (
        <div key={t} className="insight">{t}</div>
      ))}
    </div>
  )
}
