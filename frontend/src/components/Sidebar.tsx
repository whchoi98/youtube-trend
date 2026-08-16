import type { HomeRow, RowKind } from '../types'

/** 행 식별자 — 사이드바 선택(focus)과 홈 행을 잇는 키. */
export function rowKey(row: HomeRow): string {
  if (row.kind === 'category') return `cat-${row.categoryId}`
  if (row.kind === 'region') return `rgn-${row.regionCode}`
  return `${row.kind}:${row.title}`
}

/** 사이드바용 짧은 라벨 — 행 제목의 수식을 걷어낸다. */
function sideLabel(row: HomeRow): string {
  if (row.kind === 'top10') return '전체 급상승'
  if (row.kind === 'accel') return '조회수 급증'
  if (row.kind === 'chart') return 'YouTube Music'
  if (row.kind === 'spotlight') return 'AWS'
  return row.title
    .replace('은 지금', '')
    .replace('는 지금', '')
    .replace('가 보는 중', '')
}

/** 주제 묶음 — 사이드바 섹션 헤더로 표기한다. */
const GROUPS: { label: string; kinds: RowKind[] }[] = [
  { label: '랭킹', kinds: ['top10', 'accel', 'chart', 'spotlight'] },
  { label: 'AI 추천', kinds: ['topic', 'age'] },
  { label: '분야', kinds: ['category'] },
  { label: '국가', kinds: ['region'] },
]

/** 넷플릭스식 좌측 사이드바 — 주제를 고르면 그 주제의 TOP 20을 큰 순위
 *  숫자 스타일로 보여준다. 항목은 홈 행에서 파생되므로 데이터가 있는 주제만
 *  나타난다(좁은 화면에서는 가로 칩 바로 전환). */
export function Sidebar({ rows, focus, onSelect }: {
  rows: HomeRow[]
  focus: string | null
  onSelect: (key: string | null) => void
}) {
  return (
    <nav className="sidebar" aria-label="주제 선택">
      <button
        type="button"
        className={focus === null ? 'side-item active' : 'side-item'}
        onClick={() => onSelect(null)}
      >
        홈
      </button>
      {GROUPS.map((g) => {
        const groupRows = rows.filter((r) => g.kinds.includes(r.kind))
        if (groupRows.length === 0) return null
        return (
          <div className="side-group" key={g.label}>
            <div className="side-head" aria-hidden="true">{g.label}</div>
            {groupRows.map((r) => {
              const key = rowKey(r)
              return (
                <button
                  key={key}
                  type="button"
                  className={focus === key ? 'side-item active' : 'side-item'}
                  onClick={() => onSelect(key)}
                >
                  {sideLabel(r)}
                </button>
              )
            })}
          </div>
        )
      })}
    </nav>
  )
}
