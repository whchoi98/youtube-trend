import { getTheme } from './theme'

/**
 * 차트 계열 색상 — 고정 팔레트(다크/라이트 각각 대비·CVD 검증됨).
 * recharts는 SVG fill/stroke 속성에 CSS 커스텀 프로퍼티(var())를 안정적으로
 * 반영하지 않는 경우가 있어, 테마별 고정 hex 배열을 직접 사용한다.
 */
const CATEGORICAL_LIGHT = [
  '#2a78d6', // 1 blue
  '#eb6834', // 2 orange
  '#1baf7a', // 3 aqua
  '#eda100', // 4 yellow
  '#e87ba4', // 5 magenta
  '#008300', // 6 green
  '#4a3aa7', // 7 violet
  '#e34948', // 8 red
]

const CATEGORICAL_DARK = [
  '#3987e5', // 1 blue
  '#d95926', // 2 orange
  '#199e70', // 3 aqua
  '#c98500', // 4 yellow
  '#d55181', // 5 magenta
  '#008300', // 6 green
  '#9085e9', // 7 violet
  '#e66767', // 8 red
]

/** 현재 테마에 맞는 8색 카테고리 팔레트(고정 순서 — 색상은 항목이 아닌 슬롯에 귀속). */
export function categoricalPalette(): string[] {
  return getTheme() === 'dark' ? CATEGORICAL_DARK : CATEGORICAL_LIGHT
}

/** 단일 계열(순위/조회수 라인) 강조색 — 팔레트 1번(blue) 슬롯 재사용. */
export function seriesAccent(): string {
  return categoricalPalette()[0]
}

/** 진입/이탈 막대 색상 — blue/red는 모든 테마·전체쌍 CVD 검증을 통과한 조합. */
export function enteredColor(): string {
  return categoricalPalette()[0]
}
export function exitedColor(): string {
  return categoricalPalette()[7]
}
