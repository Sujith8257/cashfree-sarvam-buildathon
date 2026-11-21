import { useRef, useState } from 'react'
import { Upload, Download, X } from 'lucide-react'
import { DialogFrame } from './ui/DialogFrame'
import { Button } from './ui/button'
import { CSV_HEADERS, validateBorrowerCsv, type NewBorrower } from '@/lib/borrowerCsv'

export function BulkImportModal({ onClose, onImport }: { onClose: () => void; onImport: (rows: NewBorrower[]) => Promise<void> }) {
  const fileInput = useRef<HTMLInputElement>(null)
  const [filename, setFilename] = useState('')
  const [borrowers, setBorrowers] = useState<NewBorrower[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [reading, setReading] = useState(false)
  const [done, setDone] = useState(false)
  const template = () => {
    const url = URL.createObjectURL(new Blob([CSV_HEADERS.join(',') + '\nDemo Borrower,+919876543210,borrower@example.com,Kannada,2026-01-01,2026-12-01,10000,5000,12.5\n'], { type: 'text/csv;charset=utf-8;' }))
    const link = document.createElement('a'); link.href = url; link.download = 'borrowers-template.csv'; link.click(); URL.revokeObjectURL(url)
  }
  const read = async (file?: File) => {
    if (!file) return
    setFilename(file.name)
    setBorrowers([]); setErrors([]); setDone(false)
    if (!file) return
    setReading(true)
    try {
      if (!file.name.toLowerCase().endsWith('.csv')) throw new Error('Choose a .csv file.')
      if (file.size > 2 * 1024 * 1024) throw new Error('Choose a CSV smaller than 2 MB.')
      const result = validateBorrowerCsv(await file.text()); setBorrowers(result.borrowers); setErrors(result.errors)
    } catch (error) { setErrors([error instanceof Error ? error.message : 'Could not read file.']) }
    finally { setReading(false) }
  }
  const submit = async () => {
    setBusy(true)
    try { await onImport(borrowers); setDone(true) }
    catch (error) { setErrors([error instanceof Error ? error.message : 'Import failed. Please try again.']) }
    finally { setBusy(false) }
  }
  return <DialogFrame title="Import borrowers from CSV" onClose={() => { if (!busy && !reading) onClose() }}>
    <div className="w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 p-6 space-y-4 max-h-[85vh] overflow-y-auto">
      <div className="flex items-center justify-between gap-4"><h2 className="text-lg font-semibold">Import borrowers from CSV</h2><Button variant="ghost" size="icon" aria-label="Close import" onClick={onClose} disabled={busy || reading}><X size={18}/></Button></div>
      {done ? <><p role="status">Imported {borrowers.length} borrowers successfully.</p><Button onClick={onClose}>Done</Button></> : <>
        <p className="text-sm">Upload up to 1,000 borrowers (2 MB). Required columns: name, phone_number, principal_amount. Dates use YYYY-MM-DD. Borrower IDs are generated automatically.</p>
        <Button variant="outline" onClick={template}><Download size={16}/>Download CSV template</Button>
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 p-5 space-y-3">
          <p className="text-sm font-medium">Upload your borrower CSV</p>
          <input ref={fileInput} id="borrower-csv" type="file" accept=".csv,text/csv" hidden disabled={busy || reading} onChange={event => { const file = event.target.files?.[0]; void read(file); event.target.value = '' }}/>
          <div className="flex flex-wrap items-center gap-3"><Button onClick={() => fileInput.current?.click()} disabled={busy || reading} aria-controls="borrower-csv"><Upload size={16}/>{reading ? 'Reading CSV…' : filename ? 'Choose another CSV' : 'Upload CSV'}</Button><span className="text-sm break-all" role="status">{filename || 'No CSV selected'}</span></div>
          <p className="text-xs">Choose a .csv file from your device. Review the preview below, then select Import borrowers.</p>
        </div>
        <p className="text-sm">This adds new borrower records. Existing records are not updated. Importing the same file again creates additional records.</p>
        {reading && <p role="status">Reading CSV…</p>}
        {!!errors.length && <div role="alert" className="form-error"><p>{errors.length} issue(s). No borrowers have been imported. Fix the file and upload it again.</p><ul>{errors.slice(0, 20).map((error, i) => <li key={i}>{error}</li>)}</ul>{errors.length > 20 && <p>Showing the first 20 issues.</p>}</div>}
        {!!borrowers.length && !errors.length && <><p role="status">{borrowers.length} borrowers ready to import. Preview of the first five:</p><div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead><tr><th>Name</th><th>Phone</th><th>Outstanding (INR)</th></tr></thead><tbody>{borrowers.slice(0, 5).map((borrower, i) => <tr key={i}><td className="py-2 pr-3">{borrower.name}</td><td className="pr-3">{borrower.phone_number}</td><td>{borrower.outstanding_amount.toLocaleString('en-IN')}</td></tr>)}</tbody></table></div></>}
        <div className="flex justify-end gap-2"><Button variant="outline" onClick={onClose} disabled={busy || reading}>Cancel</Button><Button onClick={submit} disabled={busy || reading || !borrowers.length || !!errors.length}><Upload size={16}/>{busy ? 'Importing…' : `Import ${borrowers.length || ''} borrowers`}</Button></div>
      </>}
    </div>
  </DialogFrame>
}
