import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, fetchJson } from './api'
import type { HomeCard, HomeData, HomeRow } from './types'
import { formatClockKst } from './format'
import { getTheme, setTheme } from './theme'
import { Hero } from './components/Hero'
import { InsightChips } from './components/InsightChips'
import { Row } from './components/Row'
import { TrendsPanel } from './components/TrendsPanel'
import { VideoSeriesPanel } from './components/VideoSeriesPanel'
import { BriefPanel } from './components/BriefPanel'
import { QuizModal } from './components/QuizModal'
import { ThemeModal } from './components/ThemeModal'
import { SelectedTrend } from './components/SelectedTrend'

type HomeState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: HomeData }

const POLL_MS = 60_000

export default function App() {
  const [home, setHome] = useState<HomeState>({ status: 'loading' })
  const [quizRow, setQuizRow] = useState<HomeRow | null>(null)
  const [theme, setThemeState] = useState<string>(() => getTheme())
  const [showQuiz, setShowQuiz] = useState(false)
  const [showTheme, setShowTheme] = useState(false)
  // 타일에서 선택한 콘텐츠 — 히어로가 넷플릭스 빌보드처럼 이 콘텐츠로 바뀐다
  const [selected, setSelected] = useState<HomeCard | null>(null)
  // 하단 패널(점유율/브리핑)은 수동 새로고침 때만 remount로 재조회한다
  const [panelKey, setPanelKey] = useState(0)

  // 폴링과 수동 새로고침이 겹칠 수 있다 — 세대 가드로 늦은 응답을 폐기한다
  const seqRef = useRef(0)
  const loadHome = useCallback((silent = false) => {
    const seq = ++seqRef.current
    if (!silent) setHome({ status: 'loading' })
    fetchJson<HomeData>('/api/home')
      .then((data) => {
        if (seq !== seqRef.current) return
        setHome({ status: 'ready', data })
      })
      .catch((err: unknown) => {
        if (seq !== seqRef.current) return
        if (silent) return // 자동 갱신 실패는 기존 화면을 유지한다
        const message = err instanceof ApiError
          ? (err.body.error ?? '홈을 불러오지 못했습니다')
          : '네트워크 오류'
        setHome({ status: 'error', message })
      })
  }, [])

  useEffect(() => {
    loadHome()
    const id = setInterval(() => loadHome(true), POLL_MS)
    return () => clearInterval(id)
  }, [loadHome])

  const refresh = () => {
    loadHome()
    setPanelKey((k) => k + 1)
  }

  const selectTheme = (id: string) => {
    setTheme(id)
    setThemeState(id)
  }

  const selectCard = (card: HomeCard) => {
    setSelected(card)
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' })
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="logo">YOUTUBE TREND MONITOR</div>
        {home.status === 'ready' && (
          <span className="last-at">수집 {formatClockKst(home.data.capturedAt)}</span>
        )}
        <div className="spacer" />
        <button type="button" className="tb-btn" onClick={refresh}>새로고침</button>
        <button type="button" className="tb-btn" onClick={() => setShowTheme(true)}>🎨 테마</button>
      </header>

      {home.status === 'loading' && <div className="msg">트렌드 불러오는 중…</div>}

      {home.status === 'error' && (
        <div className="msg">
          <p>{home.message}</p>
          <button type="button" className="tb-btn" onClick={() => loadHome()}>다시 시도</button>
        </div>
      )}

      {home.status === 'ready' && (
        <>
          <Hero
            hero={home.data.hero}
            selected={selected}
            onQuiz={() => setShowQuiz(true)}
            onClear={() => setSelected(null)}
          />
          {selected && (
            <section className="panel hero-trend">
              <h2>선택한 콘텐츠 추이</h2>
              <SelectedTrend card={selected} />
            </section>
          )}
          <InsightChips items={home.data.insights} />

          <main className="rows">
            {quizRow && <Row row={quizRow} hint="퀴즈 맞춤" onTile={selectCard} />}
            {home.data.rows.map((row) => (
              <Row
                key={`${row.kind}:${row.title}`}
                row={row}
                hint={row.kind === 'topic' || row.kind === 'age' ? 'AI 태깅' : undefined}
                onTile={selectCard}
              />
            ))}
            {!home.data.tagged && home.data.llmEnabled && (
              <div className="msg small">🏷️ AI 태깅 진행 중 — 잠시 후 주제별 행이 추가됩니다</div>
            )}
          </main>

          <div className="bottom">
            <section className="panel">
              <h2>영상 시계열</h2>
              <VideoSeriesPanel key={`series-${panelKey}`} />
            </section>
            <section className="panel">
              <h2>카테고리 점유율 추이</h2>
              <TrendsPanel key={`trends-${panelKey}`} />
            </section>
            <section className="panel">
              <h2>AI 브리핑</h2>
              <BriefPanel key={`brief-${panelKey}`} />
            </section>
          </div>
        </>
      )}

      {showQuiz && (
        <QuizModal onClose={() => setShowQuiz(false)} onResult={setQuizRow} />
      )}
      {showTheme && (
        <ThemeModal current={theme} onSelect={selectTheme} onClose={() => setShowTheme(false)} />
      )}
    </div>
  )
}
