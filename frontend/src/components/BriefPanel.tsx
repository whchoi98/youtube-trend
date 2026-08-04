import { useState } from 'react'
import { ApiError, postJson } from '../api'

type Mode = 'now' | 'daily' | 'report'

interface BriefResp { brief: string; baseline?: string; cached: boolean }
interface ReportResp { report: string; cached: boolean }
interface Result { heading: string; text: string }

const LABELS: Record<Mode, string> = {
  now: '오늘의 브리핑',
  daily: '어제와 비교',
  report: '추이 리포트',
}

function hoursAgo(iso: string): number {
  return Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 3_600_000))
}

function headingFor(mode: Mode, baseline?: string): string {
  if (mode === 'daily' && baseline) return `어제와 비교 (${hoursAgo(baseline)}시간 전 기준)`
  return LABELS[mode]
}

/** 오늘의 브리핑 / 어제와 비교 / 추이 리포트 — LLM 호출 3버튼 패널. */
export function BriefPanel() {
  const [busy, setBusy] = useState<Mode | null>(null)
  const [disabled, setDisabled] = useState(false)
  const [lockMessage, setLockMessage] = useState<string | null>(null)
  const [result, setResult] = useState<Result | null>(null)

  const run = async (mode: Mode) => {
    setBusy(mode)
    try {
      if (mode === 'report') {
        const r = await postJson<ReportResp>('/api/trends/report', { scope: 'all' })
        setResult({ heading: headingFor(mode), text: r.report })
      } else {
        const r = await postJson<BriefResp>('/api/brief', { scope: 'all', mode })
        setResult({ heading: headingFor(mode, r.baseline), text: r.brief })
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        // 키 미설정 등 — 브리핑 기능 전체를 잠근다(개별 버튼 재시도로는 해소되지 않음)
        setDisabled(true)
        setLockMessage(e.body.error ?? '브리핑 기능이 설정되지 않았습니다')
      } else if (e instanceof ApiError && e.status === 409) {
        setResult({ heading: LABELS[mode], text: e.body.error ?? '아직 데이터가 없습니다' })
      } else {
        setResult({ heading: LABELS[mode], text: e instanceof ApiError ? (e.body.error ?? '요청 실패') : '요청 실패' })
      }
    } finally {
      setBusy(null)
    }
  }

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

      {!disabled && result && (
        <div className="brief-output">
          <h3>{result.heading}</h3>
          <p className="brief-text">{result.text}</p>
        </div>
      )}
    </div>
  )
}
