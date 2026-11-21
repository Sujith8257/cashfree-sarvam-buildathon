import { DialogFrame } from './ui/DialogFrame'
import React, { useState } from 'react'
import { Customer, AgentInteraction } from '@/types/database'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { X, Save, PhoneCall } from 'lucide-react'

interface NewInteractionModalProps {
  customers: Customer[]
  defaultCustomerId?: number
  isOpen: boolean
  onClose: () => void
  onSubmit: (interaction: Omit<AgentInteraction, 'interaction_id'>) => Promise<void>
}

export const NewInteractionModal: React.FC<NewInteractionModalProps> = ({
  customers,
  defaultCustomerId,
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [customerId, setCustomerId] = useState<number>(defaultCustomerId || (customers[0]?.customer_id ?? 101))
  const [callDatetime, setCallDatetime] = useState<string>(new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16))
  const [callStatus, setCallStatus] = useState<string>('Completed')
  const [languageUsed, setLanguageUsed] = useState<string>(customers.find(c => c.customer_id === defaultCustomerId)?.language || 'English')
  const [callSummary, setCallSummary] = useState<string>('')
  const [callTranscript, setCallTranscript] = useState<string>('')
  const [customerFeedback, setCustomerFeedback] = useState<string>('')
  const [paymentStatus, setPaymentStatus] = useState<string>('Promised to Pay')
  const [promiseToPayDate, setPromiseToPayDate] = useState<string>('')
  const [promiseToPayAmount, setPromiseToPayAmount] = useState<string>('')
  const [callRecording, setCallRecording] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await onSubmit({
        customer_id: Number(customerId),
        call_datetime: new Date(callDatetime).toISOString(),
        call_status: callStatus,
        language_used: languageUsed,
        call_summary: callSummary || null,
        call_transcript: callTranscript || null,
        customer_feedback: customerFeedback || null,
        payment_status: paymentStatus || null,
        promise_to_pay_date: promiseToPayDate || null,
        promise_to_pay_amount: promiseToPayAmount ? parseFloat(promiseToPayAmount) : null,
        call_recording: callRecording || null,
      })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <DialogFrame title="Log call interaction" onClose={onClose}>
      <div className="relative w-full max-w-2xl rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 px-6 py-4 bg-slate-50/50 dark:bg-slate-950/40">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-blue-600/10 text-blue-600 flex items-center justify-center">
              <PhoneCall className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Log Agent Call Interaction
              </h2>
              <p className="text-xs text-slate-500">Capture the conversation and agree on the next step.</p>
            </div>
          </div>
          <Button aria-label="Close dialog" variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 text-slate-500">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Target Customer *
              </label>
              <select
                value={customerId}
                onChange={(e) => {setCustomerId(Number(e.target.value)); setLanguageUsed(customers.find(c => c.customer_id === Number(e.target.value))?.language || 'English')}}
                className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
                required
              >
                {customers.map((c) => (
                  <option key={c.customer_id} value={c.customer_id}>
                    #{c.customer_id} - {c.name} ({c.phone_number})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Call Date & Time
              </label>
              <Input
                type="datetime-local"
                value={callDatetime}
                onChange={(e) => setCallDatetime(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Call Status
              </label>
              <select
                value={callStatus}
                onChange={(e) => setCallStatus(e.target.value)}
                className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
              >
                <option value="Completed">Completed</option>
                <option value="Busy">Busy</option>
                <option value="No Answer">No Answer</option>
                <option value="Failed">Failed</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Language Used
              </label>
              <select
                value={languageUsed}
                onChange={(e) => setLanguageUsed(e.target.value)}
                className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
              >
                <option value="English">English</option>
                <option value="Spanish">Spanish</option>
                <option value="Hindi">Hindi</option>
                <option value="French">French</option>
                <option value="German">German</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Payment Status
              </label>
              <select
                value={paymentStatus}
                onChange={(e) => setPaymentStatus(e.target.value)}
                className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
              >
                <option value="Promised to Pay">Promised to Pay</option>
                <option value="Paid">Paid</option>
                <option value="Pending Review">Pending Review</option>
                <option value="Disputed">Disputed</option>
                <option value="Refused">Refused</option>
              </select>
            </div>
          </div>

          {/* Promise to pay row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-3 bg-purple-50/40 dark:bg-purple-950/20 rounded-xl border border-purple-200/50">
            <div>
              <label className="text-xs font-semibold text-purple-900 dark:text-purple-300 mb-1 block">
                Promise to Pay Amount (₹)
              </label>
              <Input
                type="number"
                step="0.01" min="0"
                placeholder="e.g. 500.00"
                value={promiseToPayAmount}
                onChange={(e) => setPromiseToPayAmount(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-purple-900 dark:text-purple-300 mb-1 block">
                Promise to Pay Date
              </label>
              <Input
                type="date"
                value={promiseToPayDate}
                onChange={(e) => setPromiseToPayDate(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
              Call Summary
            </label>
            <textarea
              rows={2}
              value={callSummary}
              onChange={(e) => setCallSummary(e.target.value)}
              placeholder="Summary of conversation, outcome, and agreed terms..."
              className="w-full rounded-md border border-slate-200 bg-white p-2.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
              Customer Feedback & Tone
            </label>
            <Input
              type="text"
              value={customerFeedback}
              onChange={(e) => setCustomerFeedback(e.target.value)}
              placeholder="e.g. Cooperative, apologized for delay, requested email receipt..."
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
              Call Transcript
            </label>
            <textarea
              rows={4}
              value={callTranscript}
              onChange={(e) => setCallTranscript(e.target.value)}
              placeholder="[Agent]: Hello...&#10;[Customer]: Hi, I received your call..."
              className="w-full rounded-md border border-slate-200 bg-white p-2.5 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
              Call Recording Audio URL (optional)
            </label>
            <Input
              type="url"
              value={callRecording}
              onChange={(e) => setCallRecording(e.target.value)}
              placeholder="https://.../audio.mp3"
            />
          </div>

          {/* Footer inside form */}
          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={loading} className="gap-1.5">
              <Save className="h-4 w-4" />
              {loading ? 'Saving...' : 'Save Interaction'}
            </Button>
          </div>
        </form>
      </div>
    </DialogFrame>
  )
}
