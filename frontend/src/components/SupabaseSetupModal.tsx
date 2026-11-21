import setupSql from '../../supabase/setup.sql?raw'
import { DialogFrame } from './ui/DialogFrame'
import React, { useState } from 'react'
import { Button } from './ui/button'
import { Input } from './ui/input'
import {
  X,
  Database,
  Check,
  Copy,
  ExternalLink,
  RefreshCw,
  Trash2,
  AlertTriangle,
} from 'lucide-react'
import {
  getStoredSupabaseConfig,
  saveSupabaseConfig,
  saveLocalCustomers,
  saveLocalInteractions,
} from '@/lib/supabaseClient'
import { INITIAL_CUSTOMERS, INITIAL_INTERACTIONS } from '@/data/mockData'

interface SupabaseSetupModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: () => void
}

export const SupabaseSetupModal: React.FC<SupabaseSetupModalProps> = ({
  isOpen,
  onClose,
  onSave,
}) => {
  const current = getStoredSupabaseConfig()
  const [url, setUrl] = useState(current.url)
  const [anonKey, setAnonKey] = useState(current.anonKey)
  const [copiedSql, setCopiedSql] = useState(false)
  const [activeTab, setActiveTab] = useState<'config' | 'sql'>('config')

  if (!isOpen) return null

  const handleSave = () => {
    saveSupabaseConfig(url, anonKey)
    onSave()
    onClose()
  }

  const handleResetDemoData = () => {
    if (confirm('Reset to initial sample demo data? Any local edits will be refreshed.')) {
      saveLocalCustomers(INITIAL_CUSTOMERS)
      saveLocalInteractions(INITIAL_INTERACTIONS)
      onSave()
      onClose()
    }
  }

  const sqlSnippet = setupSql

  const handleCopySql = () => {
    navigator.clipboard.writeText(sqlSnippet)
    setCopiedSql(true)
    setTimeout(() => setCopiedSql(false), 2000)
  }

  return (
    <DialogFrame title="Database connection and setup" onClose={onClose}>
      <div className="relative w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 px-6 py-4 bg-slate-50/50 dark:bg-slate-950/40">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-emerald-600/10 text-emerald-600 flex items-center justify-center">
              <Database className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Supabase Connection & Setup
              </h2>
              <p className="text-xs text-slate-500">
                Connect your live project or view the SQL table scripts
              </p>
            </div>
          </div>
          <Button aria-label="Close dialog" variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 text-slate-500">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 px-6">
          <button
            type="button"
            onClick={() => setActiveTab('config')}
            className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'config'
                ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
            }`}
          >
            Project Credentials
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('sql')}
            className={`py-2.5 px-3 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
              activeTab === 'sql'
                ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
            }`}
          >
            SQL Table Schemas
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {activeTab === 'config' ? (
            <div className="space-y-4">
              <div className="p-3 rounded-lg bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200/60 dark:border-blue-900/40 text-xs text-blue-800 dark:text-blue-300">
                Enter your Supabase Project URL and Anon/Public Key to sync with your live Supabase
                database. If left empty, the application runs smoothly using local mock data.
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                  Supabase Project URL
                </label>
                <Input
                  type="url"
                  placeholder="https://xyzcompany.supabase.co"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                  Supabase Anon Key
                </label>
                <Input
                  type="password"
                  placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                  value={anonKey}
                  onChange={(e) => setAnonKey(e.target.value)}
                />
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-slate-200 dark:border-slate-800">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleResetDemoData}
                  className="text-xs text-slate-500 hover:text-rose-600 gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Reset Local Demo Data
                </Button>

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setUrl('')
                      setAnonKey('')
                    }}
                  >
                    Clear Credentials
                  </Button>
                  <Button type="button" size="sm" onClick={handleSave}>
                    Save & Reconnect
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">
                  Run this in your Supabase SQL Editor:
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopySql}
                  className="h-7 text-xs gap-1.5"
                >
                  {copiedSql ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-600" /> Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" /> Copy SQL
                    </>
                  )}
                </Button>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-slate-200 overflow-x-auto leading-relaxed max-h-[340px]">
                <pre>{sqlSnippet}</pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </DialogFrame>
  )
}
