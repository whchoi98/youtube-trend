import { THEMES } from '../themes'
import { Modal } from './Modal'

/** 테마 10종 선택 모달 — 스와치는 themes.ts의 미리보기 hex를 쓴다. */
export function ThemeModal({ current, onSelect, onClose }: {
  current: string
  onSelect: (id: string) => void
  onClose: () => void
}) {
  return (
    <Modal onClose={onClose} label="테마 선택">
      <h3>🎨 테마 선택</h3>
      <div className="themes">
        {THEMES.map((t) => (
          <button
            key={t.id}
            type="button"
            className={current === t.id ? 'theme-card sel' : 'theme-card'}
            aria-pressed={current === t.id}
            onClick={() => onSelect(t.id)}
          >
            <span className="sw" aria-hidden="true">
              {t.swatch.map((c) => (
                <i key={c} style={{ background: c }} />
              ))}
            </span>
            {t.name}
          </button>
        ))}
      </div>
    </Modal>
  )
}
