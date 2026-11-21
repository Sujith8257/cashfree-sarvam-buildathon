import { useRef, useState } from 'react'
import { Plus, ChevronDown, Check } from 'lucide-react'
import { Button } from './ui/button'
import { Input } from './ui/input'

const languages = [
  ['Telugu', 'తెలుగు'], ['English', 'English'], ['Tamil', 'தமிழ்'],
  ['Hindi', 'हिन्दी'], ['Kannada', 'ಕನ್ನಡ'], ['Malayalam', 'മലയാളം'],
]
const storageKey = 'cashfree_custom_languages'
function savedLanguages(): string[] {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(storageKey) || '[]')
    return Array.isArray(saved) ? saved.filter((name): name is string => typeof name === 'string' && !!name.trim() && name.length <= 50) : []
  } catch { return [] }
}

export function LanguageSelect({ value, onChange, id, label = 'Language' }: {
  value: string; onChange: (value: string) => void; id: string; label?: string
}) {
  const trigger = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const [custom, setCustom] = useState(savedLanguages)
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const options = [...languages, ...custom.filter(name => !languages.some(([base]) => base.toLowerCase() === name.toLowerCase())).map(name => [name, name])]
  const add = () => {
    const name = draft.trim().replace(/\s+/g, ' ')
    if (!name || name.length > 50) { setError('Enter a language name of 1–50 characters.'); return }
    const existing = options.find(([option]) => option.toLowerCase() === name.toLowerCase())
    if (existing) onChange(existing[0])
    else {
      const next = [...new Set([...savedLanguages(), ...custom, name])]
      setCustom(next)
      try { localStorage.setItem(storageKey, JSON.stringify(next)) } catch { /* Still usable for this form when browser storage is unavailable. */ }
      onChange(name)
    }
    setDraft(''); setError(''); setAdding(false)
  }
  return <div className="space-y-2">
    <div className="language-menu" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}>
      <button ref={trigger} type="button" id={id} className="language-menu-trigger" aria-label={label} aria-haspopup="menu" aria-expanded={open} aria-controls={`${id}-options`} onClick={() => setOpen(!open)} onKeyDown={event => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
          event.preventDefault(); setOpen(true)
          const root = event.currentTarget.parentElement
          requestAnimationFrame(() => {
            const items = root?.querySelectorAll<HTMLButtonElement>('[role^="menuitem"]')
            const index = event.key === 'ArrowUp' ? (items?.length || 1) - 1 : 0
            items?.[index]?.focus()
          })
        }
      }}><span>{value}</span><ChevronDown size={16} aria-hidden="true"/></button>
      {open && <div id={`${id}-options`} role="menu" aria-label={label} className="language-menu-options" onKeyDown={event => {
        const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role^="menuitem"]'))
        const index = items.indexOf(document.activeElement as HTMLButtonElement)
        if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
          event.preventDefault()
          const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length
          items[next]?.focus()
        }
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); setOpen(false); trigger.current?.focus() }
      }}>
        {(options.some(([name]) => name === value) ? options : [[value, value], ...options]).map(([name]) => <button type="button" role="menuitemradio" aria-checked={name === value} key={name} onClick={() => { onChange(name); setAdding(false); setOpen(false); trigger.current?.focus() }}><span>{name}</span>{name === value && <Check size={15} aria-hidden="true"/>}</button>)}
        <button type="button" role="menuitem" className="language-menu-add" onClick={() => { setAdding(true); setError(''); setOpen(false) }}><Plus size={15} aria-hidden="true"/>Add new language…</button>
      </div>}
    </div>
    {adding && <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 space-y-2">
      <label htmlFor={`${id}-new`} className="block text-xs font-medium">New language name</label>
      <Input id={`${id}-new`} autoFocus placeholder="e.g. Marathi" value={draft} maxLength={50} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} onChange={event => { setDraft(event.target.value); setError('') }} onKeyDown={event => {
        if (event.key === 'Enter') { event.preventDefault(); add() }
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); setAdding(false) }
      }}/>
      {error && <p id={`${id}-error`} className="form-error" role="alert">{error}</p>}
      <div className="flex flex-wrap gap-2"><Button size="sm" onClick={add}><Plus size={14}/>Add language</Button><Button size="sm" variant="ghost" onClick={() => { setAdding(false); setDraft(''); setError('') }}>Cancel</Button></div>
      <p className="text-xs text-slate-500">Added languages are remembered in this browser.</p>
    </div>}
  </div>
}
