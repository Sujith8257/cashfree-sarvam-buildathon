import { DialogFrame } from './ui/DialogFrame'
import React from 'react'
import { AgentInteraction, Customer } from '@/types/database'
import { Button } from './ui/button'
import { CallStatusBadge, PaymentStatusBadge } from './StatusBadges'
import { AudioPlayer } from './AudioPlayer'
import { TranscriptViewer } from './TranscriptViewer'
import { formatCurrency, formatDate, formatDateTime } from '@/lib/utils'
import {
  X,
  PhoneCall,
  Calendar,
  MessageSquare,
  DollarSign,
  User,
  Sparkles,
  ExternalLink,
} from 'lucide-react'

interface InteractionDetailModalProps {
  interaction: AgentInteraction | null
  customer?: Customer
  isOpen: boolean
  onClose: () => void
  onViewCustomer?: (customer: Customer) => void
}

export const InteractionDetailModal: React.FC<InteractionDetailModalProps> = ({
  interaction,
  customer,
  isOpen,
  onClose,
  onViewCustomer,
}) => {
  if (!isOpen || !interaction) return null

  const hasPtp = Boolean(interaction.promise_to_pay_amount || interaction.promise_to_pay_date)

  return (
    <DialogFrame title="Call interaction details" onClose={onClose}>
      <div className="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 px-6 py-4 bg-slate-50/50 dark:bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-emerald-600/10 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400 flex items-center justify-center font-bold">
              <PhoneCall className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  Call Interaction #{interaction.interaction_id}
                </h2>
                <CallStatusBadge status={interaction.call_status} />
                <PaymentStatusBadge status={interaction.payment_status} />
              </div>
              <p className="text-xs text-slate-500">
                Logged at: {formatDateTime(interaction.call_datetime)} • Language: {interaction.language_used || 'English'}
              </p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close dialog"
            className="h-8 w-8 text-slate-500 hover:text-slate-900"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Associated Customer Card */}
          {customer && (
            <div className="p-4 rounded-xl border border-blue-200/70 bg-blue-50/40 dark:border-blue-900/40 dark:bg-blue-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-full bg-blue-600 text-white flex items-center justify-center font-semibold text-xs shrink-0">
                  <User className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs text-blue-700 dark:text-blue-300 font-semibold flex items-center gap-2">
                    {customer.name}
                    <span className="text-[10px] bg-blue-100 dark:bg-blue-900 px-1.5 py-0.5 rounded text-blue-800 dark:text-blue-200 font-mono">
                      Cust ID #{customer.customer_id}
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-400">
                    {customer.phone_number} • Outstanding: {formatCurrency(customer.outstanding_amount)}
                  </div>
                </div>
              </div>

              {onViewCustomer && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    onClose()
                    onViewCustomer(customer)
                  }}
                  className="h-7 text-xs gap-1 border-blue-300 text-blue-700 hover:bg-blue-100/60 dark:border-blue-800 dark:text-blue-300"
                >
                  <ExternalLink className="h-3 w-3" /> View Profile
                </Button>
              )}
            </div>
          )}

          {/* Audio Recording Player */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
              Audio Recording
            </div>
            <AudioPlayer
              src={interaction.call_recording}
              title={`Call #${interaction.interaction_id} Audio Stream`}
            />
          </div>

          {/* Promise to Pay (PTP) Card if present */}
          {hasPtp && (
            <div className="p-4 rounded-xl border border-purple-200 bg-purple-50/50 dark:border-purple-900/50 dark:bg-purple-950/20">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-purple-700 dark:text-purple-300 mb-2">
                <DollarSign className="h-4 w-4" />
                Promise to Pay (PTP) Agreement
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-slate-500">Agreed Amount</div>
                  <div className="text-lg font-bold text-purple-700 dark:text-purple-300">
                    {formatCurrency(interaction.promise_to_pay_amount)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Scheduled Date</div>
                  <div className="text-lg font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                    <Calendar className="h-4 w-4 text-purple-500" />
                    {formatDate(interaction.promise_to_pay_date)}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* AI / Agent Summary */}
          {interaction.call_summary && (
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/40">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
                <Sparkles className="h-4 w-4 text-amber-500" />
                Call Summary
              </div>
              <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed">
                {interaction.call_summary}
              </p>
            </div>
          )}

          {/* Customer Feedback & Sentiment */}
          {interaction.customer_feedback && (
            <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/40">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">
                <MessageSquare className="h-4 w-4 text-emerald-500" />
                Customer Feedback & Tone
              </div>
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed italic">
                "{interaction.customer_feedback}"
              </p>
            </div>
          )}

          {/* Full Call Transcript */}
          <div>
            <TranscriptViewer
              transcript={interaction.call_transcript}
              customerName={customer?.name || 'Customer'}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-slate-200 dark:border-slate-800 px-6 py-3 bg-slate-50/50 dark:bg-slate-950/40 flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </DialogFrame>
  )
}
