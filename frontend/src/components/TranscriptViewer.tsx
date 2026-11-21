import React, { useState } from 'react'
import { Bot, User, Copy, Check, Search } from 'lucide-react'
import { Button } from './ui/button'

interface TranscriptViewerProps {
  transcript: string | null | undefined
  customerName?: string
}

export const TranscriptViewer: React.FC<TranscriptViewerProps> = ({
  transcript,
  customerName = 'Customer',
}) => {
  const [copied, setCopied] = useState(false)
  const [search, setSearch] = useState('')
  const [copyError, setCopyError] = useState('')

  if (!transcript) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 dark:border-slate-800 p-8 text-center text-sm text-slate-400">
        No call transcript recorded for this interaction.
      </div>
    )
  }

  const handleCopy = async () => {
    try { await navigator.clipboard.writeText(transcript); setCopied(true);setCopyError('');setTimeout(() => setCopied(false),2000) }
    catch {setCopyError('Unable to copy. Select and copy the transcript text instead.')}
  }

  // Parse lines to detect speaker
  const rawLines = transcript.split('\n').filter((l) => l.trim().length > 0)

  const parsedLines = rawLines.map((line) => {
    const isAgent = line.startsWith('[Agent]:') || line.startsWith('Agent:')
    const isCustomer =
      line.startsWith('[Customer]:') ||
      line.startsWith('Customer:') ||
      line.startsWith(`[${customerName}]:`)
    const isSystem = line.startsWith('[System]:') || line.startsWith('System:')

    let speaker = 'System'
    let content = line

    if (isAgent) {
      speaker = 'Agent'
      content = line.replace(/^\[?Agent\]?:?\s*/, '')
    } else if (isCustomer) {
      speaker = customerName
      content = line.slice(line.indexOf(':') + 1).trim()
    } else if (isSystem) {
      speaker = 'System'
      content = line.replace(/^\[?System\]?:?\s*/, '')
    }

    return { speaker, content, raw: line }
  })

  const filteredLines = search
    ? parsedLines.filter((l) =>
        l.content.toLowerCase().includes(search.toLowerCase())
      )
    : parsedLines

  return (
    <div className="rounded-xl border border-slate-200/90 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-950/40 p-4 space-y-4">
      {/* Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 dark:border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Call Transcript ({parsedLines.length} utterances)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <input
              aria-label="Search transcript" type="text"
              placeholder="Search transcript..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-7 w-44 rounded-md border border-slate-200 bg-white pl-8 pr-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-900"
            />
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="h-7 px-2 text-xs gap-1"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-emerald-600" /> Copied
              </>
            ) : (
              <>
                <Copy className="h-3 w-3 text-slate-500" /> Copy
              </>
            )}
          </Button>
        </div>
      </div>

      {copyError && <p role="alert" className="form-error">{copyError}</p>}
      {/* Messages dialogue */}
      <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
        {filteredLines.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-400">
            No matching phrases found for "{search}"
          </div>
        ) : (
          filteredLines.map((item, idx) => {
            const isAgent = item.speaker === 'Agent'
            const isSystem = item.speaker === 'System'

            if (isSystem) {
              return (
                <div
                  key={idx}
                  className="rounded-lg bg-amber-50/80 border border-amber-200/60 p-2.5 text-xs text-amber-800 dark:bg-amber-950/20 dark:border-amber-900/40 dark:text-amber-300"
                >
                  <span className="font-semibold">[System Log]:</span> {item.content}
                </div>
              )
            }

            return (
              <div
                key={idx}
                className={`flex gap-3 text-xs leading-relaxed ${
                  isAgent ? 'flex-row' : 'flex-row-reverse'
                }`}
              >
                <div
                  className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 text-white ${
                    isAgent
                      ? 'bg-blue-600 shadow-sm'
                      : 'bg-emerald-600 shadow-sm'
                  }`}
                >
                  {isAgent ? <Bot className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
                </div>

                <div
                  className={`max-w-[82%] rounded-2xl p-3 shadow-xs ${
                    isAgent
                      ? 'bg-white border border-slate-200/90 text-slate-800 rounded-tl-none dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200'
                      : 'bg-emerald-800 text-white rounded-tr-none'
                  }`}
                >
                  <div
                    className={`text-[10px] font-semibold mb-1 uppercase tracking-wider ${
                      isAgent ? 'text-blue-600 dark:text-blue-400' : 'text-white'
                    }`}
                  >
                    {item.speaker}
                  </div>
                  <div>{item.content}</div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

