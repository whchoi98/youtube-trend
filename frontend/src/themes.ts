/**
 * 테마 10종 정의. 실제 색은 styles.css의 [data-theme] CSS 변수 세트가 단일
 * 진실이고, 여기의 swatch hex는 테마 모달 미리보기용 사본이다(css와 동기 유지).
 */
export interface ThemeDef {
  id: string
  name: string
  /** 모달 스와치: [bg, accent, accent2] */
  swatch: [string, string, string]
}

export const THEMES: ThemeDef[] = [
  { id: 'neon-hunter', name: '네온 헌터', swatch: ['#0b0b12', '#c026d3', '#7c3aed'] },
  { id: 'dawn-live', name: '새벽 라이브', swatch: ['#0e1420', '#38bdf8', '#818cf8'] },
  { id: 'retro-arcade', name: '레트로 아케이드', swatch: ['#160f1e', '#fb7185', '#facc15'] },
  { id: 'deep-ocean', name: '딥 오션', swatch: ['#04121c', '#06b6d4', '#0ea5e9'] },
  { id: 'sunset-city', name: '선셋 시티', swatch: ['#1a1114', '#f97316', '#e11d48'] },
  { id: 'forest', name: '포레스트', swatch: ['#0d1610', '#22c55e', '#84cc16'] },
  { id: 'monochrome', name: '모노크롬', swatch: ['#111113', '#e4e4e7', '#a1a1aa'] },
  { id: 'cotton-candy', name: '코튼캔디', swatch: ['#fdf2f8', '#ec4899', '#8b5cf6'] },
  { id: 'cyberpunk', name: '사이버펑크', swatch: ['#090014', '#00ffc8', '#ff2ec4'] },
  { id: 'golden-hour', name: '골든아워', swatch: ['#171207', '#f59e0b', '#d97706'] },
]

export const DEFAULT_THEME = 'neon-hunter'
export const THEME_IDS = THEMES.map((t) => t.id)
