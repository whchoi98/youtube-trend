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
