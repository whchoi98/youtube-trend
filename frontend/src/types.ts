export interface Card {
  rank: number; videoId: string; title: string; channel: string;
  views: number; likes: number; category: string; categoryId: string;
  thumbnail: string; publishedAt: string;
  baseline: string | null; prevRank: number | null;
  delta: number | null; viewsPerHour: number | null;
}
export interface Category { id: string; name: string }
export interface HistoryPoint { ts: string; rank: number | null; views: number }
export interface TrendBucket { ts: string; shares: Record<string, number>; entered: number; exited: number }

/** AI 태깅 결과 — 수집 후 배치 태깅이라 없을 수 있다(카드에 tags 필드 자체가 없음). */
export interface Tags { topics: string[]; age: string | null; vibe: string | null }
export interface HomeCard extends Card { tags?: Tags }

/** 홈 스트립 행. 'quiz'는 클라이언트에서 퀴즈 결과로 만드는 행이다. */
export type RowKind = 'top10' | 'accel' | 'topic' | 'age' | 'category' | 'quiz'
export interface HomeRow { kind: RowKind; title: string; categoryId?: string; items: HomeCard[] }

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
