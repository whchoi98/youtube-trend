export interface Card {
  rank: number; videoId: string; title: string; channel: string;
  views: number; likes: number; category: string; categoryId: string;
  thumbnail: string; publishedAt: string;
  /** 간단한 소개(수집 시 200자 절단). 도입 이전 스냅샷에는 없다. */
  description?: string;
  baseline: string | null; prevRank: number | null;
  delta: number | null; viewsPerHour: number | null;
}

/** 비동기 로드 공용 상태 — 신규 컴포넌트/훅은 이 타입을 재사용한다. */
export type Loadable<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: T }
export interface Category { id: string; name: string }
export interface HistoryPoint { ts: string; rank: number | null; views: number }
export interface TrendBucket { ts: string; shares: Record<string, number>; entered: number; exited: number }

/** AI 태깅 결과 — 수집 후 배치 태깅이라 없을 수 있다(카드에 tags 필드 자체가 없음).
 *  comment는 한 줄 AI 분석(80자 상한) — 도입 이전 버킷의 태그에는 없다. */
export interface Tags { topics: string[]; age: string | null; vibe: string | null; comment?: string | null }
export interface HomeCard extends Card { tags?: Tags }

/** 홈 스트립 행. 'quiz'는 클라이언트에서 퀴즈 결과로 만드는 행이다. */
export type RowKind =
  | 'top10' | 'accel' | 'chart' | 'spotlight' | 'topic' | 'age' | 'category'
  | 'region' | 'quiz'
export interface HomeRow {
  kind: RowKind
  title: string
  categoryId?: string
  regionCode?: string
  items: HomeCard[]
}

export interface HomeHero extends HomeCard { tenureHours: number; heroThumbnail: string }
export interface HomeData {
  capturedAt: string
  tagged: boolean
  llmEnabled: boolean
  insights: string[]
  hero: HomeHero | null
  rows: HomeRow[]
}

export interface QuizAnswers { mood: string; time: string; style: string }
export interface QuizResult { type: string; items: HomeCard[] }
