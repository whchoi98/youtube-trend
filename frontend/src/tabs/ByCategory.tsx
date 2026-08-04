import { useCallback, useEffect, useState } from 'react'
import { ApiError, fetchJson } from '../api'
import type { Card as CardData, Category } from '../types'
import { CardGrid, CardSkeletonGrid } from '../components/CardGrid'

type CategoriesState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; categories: Category[] }

type CardsState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; cards: CardData[] }

function errMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.body.error ?? err.message : fallback
}

// 참고: 백엔드 /api/trending은 배열 계약이라 스냅샷 단위 degraded 플래그를 카드에
// 실어줄 수 없다. 카드가 아닌 스냅샷 속성이므로 이 탭에서는 안내 표시를 생략한다
// (YAGNI — 카테고리 폴백이 실측으로 확인되면 응답 계약 확장과 함께 재검토).
export function ByCategory() {
  const [catState, setCatState] = useState<CategoriesState>({ status: 'loading' })
  const [selected, setSelected] = useState<string | null>(null)
  const [cardState, setCardState] = useState<CardsState>({ status: 'loading' })

  const loadCategories = useCallback(() => {
    setCatState({ status: 'loading' })
    fetchJson<Category[]>('/api/categories')
      .then((categories) => {
        setCatState({ status: 'ready', categories })
        setSelected((prev) => prev ?? categories[0]?.id ?? null)
      })
      .catch((err: unknown) => {
        setCatState({ status: 'error', message: errMessage(err, '분야 목록을 불러오지 못했습니다') })
      })
  }, [])

  useEffect(() => {
    loadCategories()
  }, [loadCategories])

  const loadCards = useCallback((scope: string) => {
    setCardState({ status: 'loading' })
    fetchJson<CardData[]>(`/api/trending?scope=${scope}`)
      .then((cards) => setCardState({ status: 'ready', cards }))
      .catch((err: unknown) => {
        setCardState({ status: 'error', message: errMessage(err, '목록을 불러오지 못했습니다') })
      })
  }, [])

  useEffect(() => {
    if (selected) loadCards(selected)
  }, [selected, loadCards])

  if (catState.status === 'loading') {
    return (
      <section>
        <div className="chip-row" aria-hidden="true">
          {Array.from({ length: 8 }, (_, i) => (
            <div className="chip-skeleton skeleton-block" key={i} />
          ))}
        </div>
        <CardSkeletonGrid count={8} />
      </section>
    )
  }

  if (catState.status === 'error') {
    return (
      <section className="state-message">
        <p>{catState.message}</p>
        <button type="button" onClick={loadCategories}>다시 시도</button>
      </section>
    )
  }

  return (
    <section>
      <div className="chip-row" role="tablist" aria-label="분야 선택">
        {catState.categories.map((c) => (
          <button
            key={c.id}
            type="button"
            role="tab"
            className={selected === c.id ? 'chip active' : 'chip'}
            aria-pressed={selected === c.id}
            aria-selected={selected === c.id}
            onClick={() => setSelected(c.id)}
          >
            {c.name}
          </button>
        ))}
      </div>

      {cardState.status === 'loading' && <CardSkeletonGrid count={8} />}

      {cardState.status === 'error' && (
        <div className="state-message">
          <p>{cardState.message}</p>
          <button type="button" onClick={() => selected && loadCards(selected)}>다시 시도</button>
        </div>
      )}

      {cardState.status === 'ready' && cardState.cards.length === 0 && (
        <div className="state-message">
          <p>이 분야는 아직 수집된 목록이 없습니다.</p>
        </div>
      )}

      {cardState.status === 'ready' && cardState.cards.length > 0 && <CardGrid cards={cardState.cards} />}
    </section>
  )
}
