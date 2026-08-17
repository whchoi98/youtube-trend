/** 시계열 조회 기간 토글 — 24시간 / 일주일 / 한 달. */
export const PERIODS = [
  { hours: 24, label: '24시간' },
  { hours: 168, label: '일주일' },
  { hours: 720, label: '한 달' },
] as const

export function PeriodToggle({ value, onChange }: {
  value: number
  onChange: (hours: number) => void
}) {
  return (
    <div className="period-toggle" role="group" aria-label="조회 기간">
      {PERIODS.map((p) => (
        <button
          key={p.hours}
          type="button"
          className={value === p.hours ? 'period-btn active' : 'period-btn'}
          aria-pressed={value === p.hours}
          onClick={() => onChange(p.hours)}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
