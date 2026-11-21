import { DialogFrame } from './ui/DialogFrame'
import React, { useState } from 'react'
import { Customer } from '@/types/database'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { X, UserPlus, Save } from 'lucide-react'

interface NewCustomerModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (customer: Omit<Customer, 'customer_id'>) => Promise<void>
}

export const NewCustomerModal: React.FC<NewCustomerModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [language, setLanguage] = useState('English')
  const [lendingDate, setLendingDate] = useState(new Date().toISOString().slice(0, 10))
  const [dueDate, setDueDate] = useState('')
  const [principalAmount, setPrincipalAmount] = useState('')
  const [outstandingAmount, setOutstandingAmount] = useState('')
  const [interestRate, setInterestRate] = useState('12.5')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (!name.trim() || !phone.trim()) throw new Error('Enter the borrower’s name and phone number.')
      if (dueDate && lendingDate && dueDate < lendingDate) throw new Error('Due date must be on or after the lending date.')
      const principal = parseFloat(principalAmount) || 0
      const outstanding = outstandingAmount ? parseFloat(outstandingAmount) : principal

      await onSubmit({
        name: name.trim(),
        phone_number: phone.trim(),
        email: email.trim() || null,
        language: language.trim() || 'English',
        lending_date: lendingDate || null,
        due_date: dueDate || null,
        principal_amount: principal,
        outstanding_amount: outstanding,
        interest_rate: parseFloat(interestRate) || 0,
      })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <DialogFrame title="Add borrower" onClose={onClose}>
      <div className="relative w-full max-w-lg rounded-2xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 px-6 py-4 bg-slate-50/50 dark:bg-slate-950/40">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-emerald-600/10 text-emerald-600 flex items-center justify-center">
              <UserPlus className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Add borrower
              </h2>
              <p className="text-xs text-slate-500">Add contact details and loan information.</p>
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
                Full Name *
              </label>
              <Input
                type="text"
                placeholder="Jane Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Phone Number *
              </label>
              <Input
                type="tel"
                placeholder="+1 (555) 000-0000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Email Address
              </label>
              <Input
                type="email"
                placeholder="jane@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full h-9 rounded-md border border-slate-200 bg-white px-3 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-950"
              >
                <option value="English">English</option>
                <option value="Spanish">Spanish</option>
                <option value="Hindi">Hindi</option>
                <option value="French">French</option>
                <option value="German">German</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Lending Date
              </label>
              <Input
                type="date"
                value={lendingDate}
                onChange={(e) => setLendingDate(e.target.value)}
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Due Date
              </label>
              <Input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-50 dark:bg-slate-950/40 rounded-xl border border-slate-200/80 dark:border-slate-800">
            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Principal (₹) *
              </label>
              <Input
                type="number"
                step="0.01" min="0"
                placeholder="5000"
                value={principalAmount}
                onChange={(e) => {
                  setPrincipalAmount(e.target.value)
                  // Leave blank to use the final principal amount on save.
                }}
                required
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Outstanding (₹)
              </label>
              <Input
                type="number"
                step="0.01" min="0"
                placeholder="5000"
                value={outstandingAmount}
                onChange={(e) => setOutstandingAmount(e.target.value)}
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 block">
                Interest Rate (%) *
              </label>
              <Input
                type="number"
                step="0.01" min="0"
                placeholder="12.5"
                value={interestRate}
                onChange={(e) => setInterestRate(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-2">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={loading} className="gap-1.5">
              <Save className="h-4 w-4" />
              {loading ? 'Adding...' : 'Create borrower'}
            </Button>
          </div>
        </form>
      </div>
    </DialogFrame>
  )
}
