import { Pagination, usePagination } from './Pagination'
import React, { useState } from 'react'
import { AgentInteraction, Customer } from '@/types/database'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { CallStatusBadge, PaymentStatusBadge } from './StatusBadges'
import { formatCurrency, formatDate, formatDateTime } from '@/lib/utils'
import {
  Search,
  Filter,
  PhoneCall,
  Calendar,
  MessageSquare,
  Sparkles,
  Volume2,
  FileText,
  DollarSign,
  User,
  ArrowUpDown,
  LayoutGrid,
  List,
} from 'lucide-react'

interface InteractionsViewProps {
  interactions: AgentInteraction[]
  customers: Customer[]
  onSelectInteraction: (interaction: AgentInteraction) => void
  onNewCall: () => void
  onSelectCustomer: (customer: Customer) => void
}

export const InteractionsView: React.FC<InteractionsViewProps> = ({
  interactions,
  customers,
  onSelectInteraction,
  onNewCall,
  onSelectCustomer,
}) => {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [paymentFilter, setPaymentFilter] = useState('all')
  const [viewMode, setViewMode] = useState<'timeline' | 'table'>('timeline')

  // Customer lookup dictionary
  const customerMap = new Map<number, Customer>()
  customers.forEach((c) => customerMap.set(c.customer_id, c))

  const filtered = interactions.filter((item) => {
    const cust = customerMap.get(item.customer_id)
    const custName = cust?.name || ''
    const matchSearch =
      custName.toLowerCase().includes(search.toLowerCase()) ||
      (item.call_summary && item.call_summary.toLowerCase().includes(search.toLowerCase())) ||
      (item.call_transcript && item.call_transcript.toLowerCase().includes(search.toLowerCase())) ||
      (item.customer_feedback && item.customer_feedback.toLowerCase().includes(search.toLowerCase())) ||
      String(item.interaction_id).includes(search) ||
      String(item.customer_id).includes(search)

    const matchStatus =
      statusFilter === 'all' ||
      item.call_status?.toLowerCase() === statusFilter.toLowerCase()

    const matchPayment =
      paymentFilter === 'all' ||
      item.payment_status?.toLowerCase() === paymentFilter.toLowerCase()

    return matchSearch && matchStatus && matchPayment
  })

  const { visible, controls } = usePagination(filtered, JSON.stringify([search, statusFilter, paymentFilter]))

  return (
    <div className="space-y-4">
      {/* Search & Filter Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
        <div className="flex flex-wrap items-center gap-3 flex-1">
          {/* Search */}
          <div className="relative min-w-[220px] max-w-sm flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              aria-label="Search interactions"
              type="text"
              placeholder="Search summary, transcript, feedback, customer..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Call Status Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select
              aria-label="Filter by call outcome" value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-9 rounded-md border border-slate-200 bg-white px-2.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
            >
              <option value="all">All Call Outcomes</option>
              <option value="completed">Completed</option>
              <option value="busy">Busy</option>
              <option value="no answer">No Answer</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          {/* Payment Status Filter */}
          <div className="flex items-center gap-1.5 text-xs">
            <DollarSign className="h-3.5 w-3.5 text-slate-400" />
            <select
              aria-label="Filter by payment status" value={paymentFilter}
              onChange={(e) => setPaymentFilter(e.target.value)}
              className="h-9 rounded-md border border-slate-200 bg-white px-2.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
            >
              <option value="all">All Payment Statuses</option>
              <option value="promised to pay">Promised to Pay</option>
              <option value="paid">Paid</option>
              <option value="pending review">Pending Review</option>
              <option value="disputed">Disputed</option>
              <option value="refused">Refused</option>
            </select>
          </div>
        </div>

        {/* View toggle & Add button */}
        <div className="flex items-center gap-2 self-end md:self-center">
          <div className="flex items-center border border-slate-200 dark:border-slate-800 rounded-lg p-0.5">
            <Button
              variant={viewMode === 'timeline' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('timeline')}
              className="h-7 w-7 p-0"
              title="Feed / Timeline View"
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'table' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('table')}
              className="h-7 w-7 p-0"
              title="Dense Table View"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>

          <Button size="sm" onClick={onNewCall} className="gap-1.5 text-xs">
            <PhoneCall className="h-4 w-4" />
            Log interaction
          </Button>
        </div>
      </div>

      {/* Main List / Table */}
      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-12 text-center bg-white dark:bg-slate-900">
          <div className="mx-auto h-12 w-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
            <Search className="h-6 w-6" />
          </div>
          <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
            No agent interactions matched your filters
          </p>
          <p className="text-xs text-slate-500 mt-1">Try resetting the filters or logging a new call.</p><Button className="mt-4" variant="outline" onClick={() => {setSearch('');setStatusFilter('all');setPaymentFilter('all')}}>Reset filters</Button>
        </div>
      ) : viewMode === 'timeline' ? (
        <div className="space-y-3">
          {visible.map((item) => {
            const customer = customerMap.get(item.customer_id)
            const hasPtp = Boolean(item.promise_to_pay_amount || item.promise_to_pay_date)

            return (
              <div
                key={item.interaction_id}
                className="p-5 rounded-xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-900 hover:shadow-md hover:border-blue-400/70 transition-all flex flex-col md:flex-row md:items-start justify-between gap-4"
              >
                {/* Left block: details */}
                <div className="space-y-3 flex-1">
                  {/* Top line metadata */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-mono font-bold text-slate-500 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                      #{item.interaction_id}
                    </span>

                    {/* Customer link */}
                    {customer ? (
                      <button
                        type="button"
                        onClick={() => onSelectCustomer(customer)}
                        className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        <User className="h-3.5 w-3.5" />
                        {customer.name}
                        <span className="text-slate-400 font-normal">
                          ({customer.phone_number})
                        </span>
                      </button>
                    ) : (
                      <span className="text-xs font-semibold text-slate-700">
                        Customer #{item.customer_id}
                      </span>
                    )}

                    <CallStatusBadge status={item.call_status} />
                    <PaymentStatusBadge status={item.payment_status} />

                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      {item.language_used || 'English'}
                    </span>

                    <span className="text-xs text-slate-400 ml-auto font-medium">
                      {formatDateTime(item.call_datetime)}
                    </span>
                  </div>

                  {/* Call Summary */}
                  {item.call_summary && (
                    <div className="flex items-start gap-2 text-xs text-slate-700 dark:text-slate-300 bg-slate-50/70 dark:bg-slate-950/40 p-3 rounded-lg border border-slate-100 dark:border-slate-800/80">
                      <Sparkles className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-slate-900 dark:text-slate-200">
                          Summary:{' '}
                        </span>
                        {item.call_summary}
                      </div>
                    </div>
                  )}

                  {/* Customer feedback */}
                  {item.customer_feedback && (
                    <div className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-400 italic">
                      <MessageSquare className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-0.5" />
                      <span>"{item.customer_feedback}"</span>
                    </div>
                  )}

                  {/* Promise to Pay (PTP) highlight box */}
                  {hasPtp && (
                    <div className="flex items-center gap-3 text-xs bg-purple-50/80 dark:bg-purple-950/30 border border-purple-200/70 dark:border-purple-900/40 px-3 py-2 rounded-lg text-purple-900 dark:text-purple-300">
                      <DollarSign className="h-4 w-4 text-purple-600 shrink-0" />
                      <span className="font-semibold">Promise to Pay Commitment:</span>
                      <span>
                        Amount: <strong>{formatCurrency(item.promise_to_pay_amount)}</strong>
                      </span>
                      {item.promise_to_pay_date && (
                        <span>
                          • Due by: <strong>{formatDate(item.promise_to_pay_date)}</strong>
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Right block: actions & audio indicator */}
                <div className="flex md:flex-col items-center md:items-end justify-between gap-2 shrink-0 border-t md:border-t-0 pt-3 md:pt-0 border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    {item.call_recording && (
                      <span className="flex items-center gap-1 text-[11px] text-blue-600 bg-blue-50 dark:bg-blue-950/60 px-2 py-0.5 rounded-full font-medium">
                        <Volume2 className="h-3 w-3" /> Audio
                      </span>
                    )}
                    {item.call_transcript && (
                      <span className="flex items-center gap-1 text-[11px] text-emerald-600 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full font-medium">
                        <FileText className="h-3 w-3" /> Transcript
                      </span>
                    )}
                  </div>

                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => onSelectInteraction(item)}
                    className="h-8 text-xs gap-1.5"
                  >
                    View Details
                  </Button>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        /* Dense Table View */
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Call ID & Date</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Call Status</th>
                  <th className="py-3 px-4">Payment Status</th>
                  <th className="py-3 px-4">PTP Amount</th>
                  <th className="py-3 px-4">PTP Date</th>
                  <th className="py-3 px-4">Summary</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
                {visible.map((item) => {
                  const customer = customerMap.get(item.customer_id)

                  return (
                    <tr
                      key={item.interaction_id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900 dark:text-slate-100">
                          #{item.interaction_id}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {formatDateTime(item.call_datetime)}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        {customer ? (
                          <div
                            onClick={() => onSelectCustomer(customer)}
                            className="font-medium text-blue-600 hover:underline cursor-pointer"
                          >
                            {customer.name}
                          </div>
                        ) : (
                          <div className="text-slate-600">Cust #{item.customer_id}</div>
                        )}
                        <div className="text-[10px] text-slate-400">
                          {item.language_used || 'English'}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <CallStatusBadge status={item.call_status} />
                      </td>

                      <td className="py-3 px-4">
                        <PaymentStatusBadge status={item.payment_status} />
                      </td>

                      <td className="py-3 px-4 font-semibold text-purple-700 dark:text-purple-300">
                        {item.promise_to_pay_amount
                          ? formatCurrency(item.promise_to_pay_amount)
                          : '—'}
                      </td>

                      <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                        {formatDate(item.promise_to_pay_date)}
                      </td>

                      <td className="py-3 px-4 max-w-xs truncate text-slate-600 dark:text-slate-400">
                        {item.call_summary || '—'}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSelectInteraction(item)}
                          className="h-7 text-xs text-blue-600"
                        >
                          Details
                        </Button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <Pagination {...controls}/>
    </div>
  )
}
