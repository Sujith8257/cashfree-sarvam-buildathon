import { DialogFrame } from './ui/DialogFrame'
import React from 'react'
import { Customer, AgentInteraction } from '@/types/database'
import { Button } from './ui/button'
import { CallStatusBadge, PaymentStatusBadge } from './StatusBadges'
import { formatCurrency, formatDate, formatDateTime } from '@/lib/utils'
import {
  X,
  User,
  Phone,
  Mail,
  Globe,
  Calendar,
  DollarSign,
  Percent,
  PhoneCall,
  PlusCircle,
  FileText,
  Volume2,
} from 'lucide-react'

interface CustomerDetailModalProps {
  customer: Customer | null
  interactions: AgentInteraction[]
  isOpen: boolean
  onClose: () => void
  onSelectInteraction: (interaction: AgentInteraction) => void
  onNewCall: (customerId: number) => void
}

export const CustomerDetailModal: React.FC<CustomerDetailModalProps> = ({
  customer,
  interactions,
  isOpen,
  onClose,
  onSelectInteraction,
  onNewCall,
}) => {
  if (!isOpen || !customer) return null

  const customerCalls = interactions.filter((i) => i.customer_id === customer.customer_id)
  const paidOff = Number(customer.outstanding_amount) === 0
  const repaymentPercent = Math.max(
    0,
    Math.min(
      100,
      Math.round(
        ((Number(customer.principal_amount) - Number(customer.outstanding_amount)) /
          Number(customer.principal_amount)) *
          100
      )
    )
  )

  return (
    <DialogFrame title="Borrower profile" onClose={onClose}>
      <div className="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 px-6 py-4 bg-slate-50/50 dark:bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-blue-600/10 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 flex items-center justify-center font-bold text-base">
              {customer.name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  {customer.name}
                </h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 font-mono">
                  ID: #{customer.customer_id}
                </span>
                {paidOff && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold">
                    Settled
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Lending Date: {formatDate(customer.lending_date)} • Due Date: {formatDate(customer.due_date)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="default"
              size="sm"
              onClick={() => onNewCall(customer.customer_id)}
              className="gap-1.5 text-xs"
            >
              <PlusCircle className="h-3.5 w-3.5" />
              Log Interaction
            </Button>
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
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Quick Contact & Profile Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-lg border border-slate-200/80 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-950/20 flex items-center gap-3">
              <div className="h-8 w-8 rounded-md bg-blue-50 text-blue-600 dark:bg-blue-950/50 flex items-center justify-center shrink-0">
                <Phone className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className="text-[11px] text-slate-500 font-medium">Phone Number</div>
                <div className="text-xs font-semibold truncate text-slate-800 dark:text-slate-200">
                  {customer.phone_number}
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg border border-slate-200/80 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-950/20 flex items-center gap-3">
              <div className="h-8 w-8 rounded-md bg-purple-50 text-purple-600 dark:bg-purple-950/50 flex items-center justify-center shrink-0">
                <Mail className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className="text-[11px] text-slate-500 font-medium">Email Address</div>
                <div className="text-xs font-semibold truncate text-slate-800 dark:text-slate-200">
                  {customer.email || 'None registered'}
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg border border-slate-200/80 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-950/20 flex items-center gap-3">
              <div className="h-8 w-8 rounded-md bg-amber-50 text-amber-600 dark:bg-amber-950/50 flex items-center justify-center shrink-0">
                <Globe className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className="text-[11px] text-slate-500 font-medium">Preferred Language</div>
                <div className="text-xs font-semibold truncate text-slate-800 dark:text-slate-200">
                  {customer.language || 'English'}
                </div>
              </div>
            </div>
          </div>

          {/* Financial Breakdown Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-5 bg-gradient-to-br from-slate-50 to-white dark:from-slate-950 dark:to-slate-900">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4 flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-blue-600" />
              Loan & Financial Position
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
              <div>
                <div className="text-xs text-slate-500">Outstanding Balance</div>
                <div className="text-xl font-bold text-rose-600 dark:text-rose-400">
                  {formatCurrency(customer.outstanding_amount)}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-500">Principal Disbursed</div>
                <div className="text-xl font-bold text-slate-900 dark:text-slate-100">
                  {formatCurrency(customer.principal_amount)}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-500">Interest Rate</div>
                <div className="text-xl font-bold text-blue-600 dark:text-blue-400 flex items-center gap-1">
                  {customer.interest_rate}% <span className="text-xs text-slate-400 font-normal">p.a.</span>
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-500">Repayment Progress</div>
                <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
                  {repaymentPercent}%
                </div>
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${repaymentPercent}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Disbursed: {formatDate(customer.lending_date)}</span>
                <span>Final Due: {formatDate(customer.due_date)}</span>
              </div>
            </div>
          </div>

          {/* Call & Interaction History */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-2">
                <PhoneCall className="h-4 w-4 text-purple-600" />
                Agent Call History ({customerCalls.length})
              </h3>
            </div>

            {customerCalls.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-8 text-center text-sm text-slate-400">
                No call interactions recorded for this customer yet.
                <div className="mt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onNewCall(customer.customer_id)}
                  >
                    Log First Call
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {customerCalls.map((call) => (
                  <div
                    key={call.interaction_id}
                    onClick={() => onSelectInteraction(call)}
                    className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 hover:border-blue-400 hover:shadow-xs transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                          {formatDateTime(call.call_datetime)}
                        </span>
                        <CallStatusBadge status={call.call_status} />
                        <PaymentStatusBadge status={call.payment_status} />
                        <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                          {call.language_used || 'English'}
                        </span>
                      </div>

                      {call.call_summary && (
                        <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-1">
                          {call.call_summary}
                        </p>
                      )}

                      {call.promise_to_pay_amount && (
                        <div className="text-[11px] text-purple-600 dark:text-purple-400 font-medium flex items-center gap-1">
                          Promise: {formatCurrency(call.promise_to_pay_amount)} on {formatDate(call.promise_to_pay_date)}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                      {call.call_recording && (
                        <div className="p-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600" title="Audio recording available">
                          <Volume2 className="h-3.5 w-3.5 text-blue-600" />
                        </div>
                      )}
                      <Button variant="ghost" size="sm" className="h-7 text-xs text-blue-600 gap-1">
                        <FileText className="h-3.5 w-3.5" /> View Transcript
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
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
