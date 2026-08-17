import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, fetchJson } from './api'
import type { HistoryPoint, Loadable } from './types'

/** 영상 시계열(168h) 로드 훅 — 세대 토큰으로 늦은 응답·늦은 실패를 폐기한다.
 *  영상 시계열 패널과 선택 콘텐츠 추이 섹션이 공유한다. */
export function useVideoHistory(videoId: string, hours = 168) {
  const [history, setHistory] = useState<Loadable<HistoryPoint[]>>({ status: 'loading' })
  const seqRef = useRef(0)

  const load = useCallback((id: string) => {
    const seq = ++seqRef.current
    setHistory({ status: 'loading' })
    fetchJson<{ videoId: string; points: HistoryPoint[] }>(
      `/api/videos/${encodeURIComponent(id)}/history?hours=${hours}`,
    )
      .then((res) => {
        if (seq !== seqRef.current) return
        setHistory({ status: 'ready', data: res.points })
      })
      .catch((err: unknown) => {
        if (seq !== seqRef.current) return
        setHistory({
          status: 'error',
          message: err instanceof ApiError
            ? (err.body.error ?? '시계열을 불러오지 못했습니다')
            : '시계열을 불러오지 못했습니다',
        })
      })
  }, [hours])

  useEffect(() => {
    if (videoId) load(videoId)
    return () => {
      seqRef.current += 1 // 언마운트·영상/기간 교체 후 도착하는 응답 무효화
    }
  }, [videoId, load])

  const retry = useCallback(() => {
    if (videoId) load(videoId)
  }, [videoId, load])

  return { history, retry }
}
