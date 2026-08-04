/** 조회수/좋아요 등 큰 수를 한국식 만/억 단위로 축약한다. 예: 12345 -> "1.2만", 250000000 -> "2.5억" */
export function formatCount(n: number): string {
  const trimmed = (v: number) => v.toFixed(1).replace(/\.0$/, '')
  if (n >= 100_000_000) return `${trimmed(n / 100_000_000)}억`
  if (n >= 10_000) return `${trimmed(n / 10_000)}만`
  return n.toLocaleString('ko-KR')
}
