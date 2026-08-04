import { useState } from 'react'
import { TopAll } from './tabs/TopAll'
import { ByCategory } from './tabs/ByCategory'
import { Trends } from './tabs/Trends'
import { getTheme, toggleTheme, type Theme } from './theme'

type TabKey = 'all' | 'category' | 'trend'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'all', label: '전체 Top 30' },
  { key: 'category', label: '분야별 Top 10' },
  { key: 'trend', label: '추이 분석' },
]

export default function App() {
  const [tab, setTab] = useState<TabKey>('all')
  const [theme, setThemeState] = useState<Theme>(() => getTheme())
  const [reloadKey, setReloadKey] = useState(0)

  return (
    <div className="app">
      <header className="app-header">
        <h1>YouTube 트렌드</h1>
        <div className="header-actions">
          <button type="button" onClick={() => setReloadKey((k) => k + 1)}>
            새로고침
          </button>
          <button
            type="button"
            onClick={() => setThemeState(toggleTheme())}
            aria-label="테마 전환"
          >
            {theme === 'dark' ? '라이트 모드' : '다크 모드'}
          </button>
        </div>
      </header>

      <nav className="tab-bar" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={tab === t.key ? 'tab active' : 'tab'}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="app-main">
        {tab === 'all' && <TopAll key={reloadKey} />}
        {tab === 'category' && <ByCategory key={reloadKey} />}
        {tab === 'trend' && <Trends key={reloadKey} />}
      </main>
    </div>
  )
}
