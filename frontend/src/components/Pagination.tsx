import { useState } from 'react'
import { Button } from './ui/button'

export function usePagination<T>(items: T[], filterKey: string) {
  const [size, setSize] = useState(10)
  const [position, setPosition] = useState({ key: filterKey, page: 1 })
  const pages = Math.max(1, Math.ceil(items.length / size))
  const page = position.key === filterKey ? Math.min(position.page, pages) : 1
  return {
    visible: items.slice((page - 1) * size, page * size),
    controls: { total: items.length, size, page, pages,
      onPage: (next: number) => setPosition({ key: filterKey, page: Math.max(1, Math.min(next, pages)) }),
      onSize: (next: number) => { setSize(next); setPosition({ key: filterKey, page: 1 }) },
    },
  }
}

export function Pagination({ total, size, page, pages, onPage, onSize }: {
  total: number; size: number; page: number; pages: number; onPage: (page: number) => void; onSize: (size: number) => void
}) {
  return <nav aria-label="Table pagination" className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
    <span aria-live="polite">{total ? (page - 1) * size + 1 : 0}–{Math.min(page * size, total)} of {total} records</span>
    <div className="flex flex-wrap items-center gap-3">
      <label className="flex items-center gap-2">Rows per page<select className="rounded border px-2 py-1 bg-white dark:bg-slate-900" value={size} onChange={event => onSize(Number(event.target.value))}>{[10, 25, 50].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      <Button variant="outline" size="sm" disabled={page === 1} onClick={() => onPage(page - 1)}>Previous</Button>
      <span>Page {page} of {pages}</span>
      <Button variant="outline" size="sm" disabled={page === pages} onClick={() => onPage(page + 1)}>Next</Button>
    </div>
  </nav>
}
