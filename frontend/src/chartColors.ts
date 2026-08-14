/**
 * 차트 계열 색상 — 테마 무관 고정 팔레트. 테마 10종이 전부 어두운/밝은 카드
 * 배경 위에 차트를 올리므로, 테마별 분기 대신 양쪽에서 대비가 검증된 중간
 * 채도 hex를 슬롯 순서 고정으로 쓴다. recharts는 SVG fill/stroke에 CSS
 * 커스텀 프로퍼티(var())를 안정적으로 반영하지 않으므로 hex 직접 사용.
 */
const CATEGORICAL = [
  '#3b82f6', // 1 blue
  '#f59e0b', // 2 amber
  '#10b981', // 3 emerald
  '#ef4444', // 4 red
  '#8b5cf6', // 5 violet
  '#ec4899', // 6 pink
  '#14b8a6', // 7 teal
  '#64748b', // 8 slate
]

/** 8색 카테고리 팔레트(고정 순서 — 색상은 항목이 아닌 슬롯에 귀속). */
export function categoricalPalette(): string[] {
  return CATEGORICAL
}

/** 단일 계열(순위/조회수 라인) 강조색 — 팔레트 1번(blue) 슬롯 재사용. */
export function seriesAccent(): string {
  return CATEGORICAL[0]
}

/** 진입/이탈 막대 색상 — blue/red는 전체쌍 CVD 검증을 통과한 조합. */
export function enteredColor(): string {
  return CATEGORICAL[0]
}
export function exitedColor(): string {
  return CATEGORICAL[3]
}
