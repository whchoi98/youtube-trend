import { DEFAULT_THEME, THEME_IDS } from './themes'

const STORAGE_KEY = 'yt-theme'

/** index.html의 head 부트스트랩 스크립트가 첫 페인트 전에 이미 data-theme을 설정해 둔다. */
export function getTheme(): string {
  const t = document.documentElement.dataset.theme ?? ''
  return THEME_IDS.includes(t) ? t : DEFAULT_THEME
}

export function setTheme(theme: string): void {
  const next = THEME_IDS.includes(theme) ? theme : DEFAULT_THEME
  document.documentElement.dataset.theme = next
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // localStorage 접근 불가(프라이빗 모드 등) — DOM 반영만으로 충분, 조용히 무시
  }
}
