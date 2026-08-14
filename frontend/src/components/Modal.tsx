import { useEffect, useRef, type KeyboardEvent, type ReactNode } from 'react'

const FOCUSABLE =
  'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

/** 공통 모달 셸 — 배경 클릭·Escape로 닫히고, 포커스를 다이얼로그 안에 가둔다.
 *  열릴 때 다이얼로그로 포커스를 옮기고 닫히면 이전 포커스를 복원한다. */
export function Modal({ onClose, label, children }: {
  onClose: () => void
  label: string
  children: ReactNode
}) {
  const boxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const restoreTo = document.activeElement as HTMLElement | null
    boxRef.current?.focus()
    return () => restoreTo?.focus()
  }, [])

  // 키 처리는 window가 아니라 다이얼로그 트리에 건다 — 포커스가 안에 갇혀
  // 있으므로 항상 도달하고, 모달이 겹쳐도 자신의 Escape만 처리한다.
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      onClose()
      return
    }
    if (e.key !== 'Tab' || !boxRef.current) return
    const focusables = boxRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)
    if (focusables.length === 0) {
      e.preventDefault()
      return
    }
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    const active = document.activeElement
    if (e.shiftKey && (active === first || active === boxRef.current)) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && active === last) {
      e.preventDefault()
      first.focus()
    }
  }

  return (
    <div
      className="modal-bg"
      onKeyDown={onKeyDown}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        ref={boxRef}
      >
        {children}
      </div>
    </div>
  )
}
