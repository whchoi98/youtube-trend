/** 조회수/좋아요 등 큰 수를 한국식 만/억 단위로 축약한다. 예: 12345 -> "1.2만", 250000000 -> "2.5억" */
export function formatCount(n: number): string {
  const trimmed = (v: number) => v.toFixed(1).replace(/\.0$/, '')
  if (n >= 100_000_000) return `${trimmed(n / 100_000_000)}억`
  if (n >= 10_000) return `${trimmed(n / 10_000)}만`
  return n.toLocaleString('ko-KR')
}

/** ISO 시각을 KST(UTC+9) "HH:MM" 시계 표기로 변환한다. 로컬 타임존과 무관. */
export function formatClockKst(iso: string): string {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const kst = new Date(t + 9 * 3_600_000)
  const hh = String(kst.getUTCHours()).padStart(2, '0')
  const mm = String(kst.getUTCMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

/** 카드/히어로에서 YouTube 시청 URL 조립 — 항상 새 탭으로 연다. */
export function youtubeUrl(videoId: string): string {
  return `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`
}

/** YouTube Music 재생 URL — 차트 유래 콘텐츠는 뮤직 앱으로 보낸다. */
export function musicUrl(videoId: string): string {
  return `https://music.youtube.com/watch?v=${encodeURIComponent(videoId)}`
}

/**
 * UTC 시 버킷 문자열("YYYY-MM-DDTHH")을 KST(UTC+9, DST 없음) 표기로 변환한다.
 * 예: "2026-08-04T15" -> "8/5 0시". Date를 +9h 이동시킨 뒤 getUTC* 접근자로 값을
 * 읽어, 실행 환경의 로컬 타임존과 무관하게 항상 KST 벽시계 값을 얻는다.
 */
export function formatTsKst(ts: string): string {
  const utc = new Date(`${ts}:00:00Z`)
  const kst = new Date(utc.getTime() + 9 * 3_600_000)
  const month = kst.getUTCMonth() + 1
  const day = kst.getUTCDate()
  const hour = kst.getUTCHours()
  return `${month}/${day} ${hour}시`
}
