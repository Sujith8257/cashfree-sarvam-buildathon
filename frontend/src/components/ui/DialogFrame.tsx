import React, { useEffect, useRef } from 'react'

export function DialogFrame({ title, onClose, children }: {title: string; onClose: () => void; children: React.ReactNode}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    const previous = document.activeElement as HTMLElement | null
    dialog?.showModal()
    const oldOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    // Associate incumbent labels without changing their visual structure.
    dialog?.querySelectorAll('label').forEach((label, index) => {
      const control = label.parentElement?.querySelector('input,select,textarea')
      if (control) { const id = control.id || `${dialog.id}-field-${index}`; control.id = id; label.htmlFor = id }
    })
    return () => { dialog?.close(); document.body.style.overflow = oldOverflow; previous?.focus() }
  }, [])
  return <dialog ref={ref} id={React.useId()} className="app-dialog" aria-label={title} onCancel={e => {e.preventDefault(); onClose()}} onClick={e => {if(e.target === e.currentTarget) onClose()}}>{children}</dialog>
}
