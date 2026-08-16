import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type Mode = 'now' | 'daily' | 'report'

/** SSE 이벤트 페이로드 — GET /api/brief/stream 계약. */
interface StepData { label: string; ms?: number | null }
interface DoneData { cached: boolean; baseline?: string }

const LABELS: Record<Mode, string> = {
  now: '오늘의 브리핑',
  daily: '어제와 비교',
  report: '추이 리포트',
}
/** UI 모드 → 스트림 엔드포인트 mode 파라미터. */
const API_MODE: Record<Mode, string> = { now: 'now', daily: 'daily', report: 'trend' }

function hoursAgo(iso: string): number {
  return Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 3_600_000))
}

function headingFor(mode: Mode, baseline?: string): string {
  if (mode === 'daily' && baseline) return `어제와 비교 (${hoursAgo(baseline)}시간 전 기준)`
  return LABELS[mode]
}

/** SSE 본문을 줄 단위로 파싱해 (event, data) 콜백으로 넘긴다. */
function parseSseChunk(buffer: string, onEvent: (event: string, data: unknown) => void): string {
  const blocks = buffer.split('\n\n')
  const rest = blocks.pop() ?? '' // 마지막 블록은 미완성일 수 있다
  for (const block of blocks) {
    let event = ''
    let data = ''
    for (const line of block.split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7)
      else if (line.startsWith('data: ')) data = line.slice(6)
    }
    if (!event) continue
    try {
      onEvent(event, data ? JSON.parse(data) : null)
    } catch {
      // 손상된 이벤트는 건너뛴다 — 스트림 전체를 죽이지 않는다
    }
  }
  return rest
}

/** LLM 브리핑 패널 — SSE 토큰 스트리밍 + 파이프라인 단계(도구 호출) 트레이스. */
export function BriefPanel() {
  const [busy, setBusy] = useState<Mode | null>(null)
  const [disabled, setDisabled] = useState(false)
  const [lockMessage, setLockMessage] = useState<string | null>(null)
  const [heading, setHeading] = useState<string | null>(null)
  const [steps, setSteps] = useState<StepData[]>([])
  const [text, setText] = useState('')
  const [status, setStatus] = useState<string | null>(null) // 오류/안내 평문
  const [failed, setFailed] = useState(false)               // in-band error 수신
  const [meta, setMeta] = useState<string | null>(null)     // 캐시 표시 등

  // 버튼 연타·언마운트 후 늦은 이벤트를 폐기하는 세대 가드 + 스트림 중단
  const seqRef = useRef(0)
  const ctrlRef = useRef<AbortController | null>(null)
  // 델타를 프레임 단위로 모아 setText 1회로 플러시 — 토큰마다 마크다운 전체
  // 재파싱이 일어나지 않게 한다
  const pendingRef = useRef('')
  const rafRef = useRef<number | null>(null)

  const flushPending = () => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    if (pendingRef.current) {
      const chunk = pendingRef.current
      pendingRef.current = ''
      setText((prev) => prev + chunk)
    }
  }

  useEffect(() => () => {
    seqRef.current += 1
    ctrlRef.current?.abort()
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
  }, [])

  const run = async (mode: Mode) => {
    const seq = ++seqRef.current
    ctrlRef.current?.abort()
    const ctrl = new AbortController()
    ctrlRef.current = ctrl

    setBusy(mode)
    setHeading(LABELS[mode])
    setSteps([])
    setText('')
    setStatus(null)
    setFailed(false)
    setMeta(null)
    pendingRef.current = ''

    try {
      const res = await fetch(`/api/brief/stream?scope=all&mode=${API_MODE[mode]}`,
        { signal: ctrl.signal })

      if (!res.ok) {
        // 스트림 시작 전 오류는 기존 HTTP 계약 그대로 온다
        const body = await res.json().catch(() => ({})) as { error?: string }
        if (seq !== seqRef.current) return
        if (res.status === 503) {
          setDisabled(true)
          setLockMessage(body.error ?? '브리핑 기능이 설정되지 않았습니다')
        } else {
          setStatus(body.error ?? '요청 실패')
        }
        return
      }

      const reader = res.body?.getReader()
      if (!reader) {
        setStatus('이 브라우저에서는 스트리밍을 지원하지 않습니다')
        return
      }
      const decoder = new TextDecoder()
      let buffer = ''

      const handle = (event: string, data: unknown) => {
        if (seq !== seqRef.current) return
        if (event === 'step') {
          setSteps((prev) => [...prev, data as StepData])
        } else if (event === 'delta') {
          pendingRef.current += (data as { text: string }).text ?? ''
          if (rafRef.current === null) {
            rafRef.current = requestAnimationFrame(() => {
              rafRef.current = null
              flushPending()
            })
          }
        } else if (event === 'done') {
          flushPending()
          const d = data as DoneData
          setHeading(headingFor(mode, d.baseline))
          setMeta(d.cached ? '캐시된 응답 (같은 시간대 재사용)' : null)
        } else if (event === 'error') {
          flushPending()
          setFailed(true)
          setStatus((data as { error?: string }).error ?? '분석 생성에 실패했습니다')
        }
      }

      for (;;) {
        const { done, value } = await reader.read()
        if (seq !== seqRef.current) return
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        buffer = parseSseChunk(buffer, handle)
      }
      if (seq === seqRef.current) flushPending()
    } catch {
      if (seq !== seqRef.current) return
      setStatus('네트워크 오류')
    } finally {
      if (seq === seqRef.current) setBusy(null)
    }
  }

  const showOutput = heading !== null && (steps.length > 0 || text || status)

  return (
    <div className="brief-panel">
      <div className="brief-actions">
        {(['now', 'daily', 'report'] as Mode[]).map((mode) => (
          <button
            key={mode}
            type="button"
            disabled={disabled || busy !== null}
            onClick={() => run(mode)}
          >
            {busy === mode && <span className="spinner" aria-hidden="true" />}
            {LABELS[mode]}
          </button>
        ))}
      </div>

      {disabled && (
        <p className="brief-locked">브리핑 비활성 — {lockMessage}</p>
      )}

      {!disabled && showOutput && (
        <div className="brief-output">
          <h3>{heading}</h3>

          {steps.length > 0 && (
            <ol className="brief-steps" aria-label="브리핑 생성 단계">
              {steps.map((s, i) => {
                const last = i === steps.length - 1
                const running = busy !== null && last && !text && !failed
                const mark = failed && last ? '✗' : running ? '⋯' : '✓'
                const cls = failed && last ? 'failed' : running ? 'running' : 'done'
                return (
                  <li key={`${i}-${s.label}`} className={cls}>
                    <span className="step-mark" aria-hidden="true">{mark}</span>
                    {s.label}
                    {typeof s.ms === 'number' && <span className="step-ms">{s.ms}ms</span>}
                  </li>
                )
              })}
            </ol>
          )}

          {text && (
            <div className="brief-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
            </div>
          )}

          {failed && text && (
            <p className="brief-text brief-error">위 내용은 생성 도중 중단된 부분 결과입니다.</p>
          )}
          {status && <p className={failed ? 'brief-text brief-error' : 'brief-text'}>{status}</p>}
          {meta && <p className="brief-meta">{meta}</p>}
        </div>
      )}
    </div>
  )
}
