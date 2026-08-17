import { useRef, useState } from 'react'
import { ApiError, postJson } from '../api'
import type { HomeRow, QuizResult } from '../types'
import { Modal } from './Modal'

// opts 값은 백엔드 QUIZ_MOODS/TIMES/STYLES와 문자열이 정확히 일치해야 한다
const QUIZ = [
  { key: 'mood', label: '지금 원하는 건?', opts: ['힐링', '도파민', '지식', '감동'] },
  { key: 'time', label: '주로 언제 보나요?', opts: ['낮', '심야', '출퇴근길'] },
  { key: 'style', label: '보는 방식은?', opts: ['몰입', '가볍게', '같이 보기'] },
] as const

type QuizKey = (typeof QUIZ)[number]['key']

/** 취향 퀴즈 3문항 — 제출하면 맞춤 추천 행을 홈 맨 위에 추가한다. */
export function QuizModal({ onClose, onResult }: {
  onClose: () => void
  onResult: (row: HomeRow) => void
}) {
  const [answers, setAnswers] = useState<Partial<Record<QuizKey, string>>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<QuizResult | null>(null)
  // 모달을 닫은 뒤 도착하는 늦은 응답이 상태를 건드리지 않도록 세대 가드
  const seqRef = useRef(0)

  const complete = QUIZ.every((q) => answers[q.key])

  const submit = () => {
    const seq = ++seqRef.current
    setBusy(true)
    setError(null)
    postJson<QuizResult>('/api/quiz', answers)
      .then((r) => {
        if (seq !== seqRef.current) return
        setBusy(false)
        setDone(r)
        onResult({ kind: 'quiz', title: `${r.type}의 추천`, items: r.items })
      })
      .catch((e: unknown) => {
        if (seq !== seqRef.current) return
        setBusy(false)
        setError(e instanceof ApiError ? (e.body.error ?? '요청 실패') : '네트워크 오류')
      })
  }

  const close = () => {
    seqRef.current += 1
    onClose()
  }

  return (
    <Modal onClose={close} label="내 취향 찾기">
      {done ? (
        <>
          <div className="quiz-result">
            <div className="muted">당신의 트렌드 유형</div>
            <div className="tname">{done.type}</div>
            <div className="muted">맞춤 추천 {done.items.length}개를 홈 맨 위에 추가했어요</div>
          </div>
          <button type="button" className="go" onClick={close}>홈에서 보기</button>
        </>
      ) : (
        <>
          <h3>내 취향 찾기</h3>
          {QUIZ.map((q) => (
            <div className="q" key={q.key}>
              <div className="ql">{q.label}</div>
              <div className="opts">
                {q.opts.map((o) => (
                  <button
                    key={o}
                    type="button"
                    className={answers[q.key] === o ? 'opt sel' : 'opt'}
                    aria-pressed={answers[q.key] === o}
                    onClick={() => setAnswers((a) => ({ ...a, [q.key]: o }))}
                  >
                    {o}
                  </button>
                ))}
              </div>
            </div>
          ))}
          {error && <p className="modal-error">{error}</p>}
          <button type="button" className="go" disabled={!complete || busy} onClick={submit}>
            {busy ? '분석 중…' : '결과 보기'}
          </button>
        </>
      )}
    </Modal>
  )
}
