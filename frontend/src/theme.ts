export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'yt-theme'

/** index.html의 head 부트스트랩 스크립트가 첫 페인트 전에 이미 data-theme을 설정해 둔다. */
export function getTheme(): Theme {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

export function setTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // localStorage 접근 불가(프라이빗 모드 등) — DOM 반영만으로 충분, 조용히 무시
  }
}

export function toggleTheme(): Theme {
  const next: Theme = getTheme() === 'dark' ? 'light' : 'dark'
  setTheme(next)
  return next
}
