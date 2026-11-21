import React from 'react'
import { Customer, AgentInteraction } from '@/types/database'
import { formatCurrency } from '@/lib/utils'
import { Users, PhoneCall, HandCoins, Wallet } from 'lucide-react'

export function MetricsOverview({ customers, interactions }: {customers: Customer[]; interactions: AgentInteraction[]}) {
  const principal = customers.reduce((s,c) => s + Number(c.principal_amount || 0), 0)
  const outstanding = customers.reduce((s,c) => s + Number(c.outstanding_amount || 0), 0)
  const progress = principal > 0 ? Math.max(0, Math.min(100, Math.round(outstanding / principal * 100))) : 0
  const promises = interactions.filter(i => i.payment_status?.toLowerCase() === 'promised to pay')
  const ptp = promises.reduce((s,i) => s + Number(i.promise_to_pay_amount || 0), 0)
  const completed = interactions.filter(i => i.call_status?.toLowerCase() === 'completed').length
  const settled = customers.filter(c => Number(c.outstanding_amount) === 0).length
  return <section className="portfolio-summary" aria-label="Portfolio metrics">
    <div className="summary-primary"><div className="metric-label"><Wallet size={17}/><span>Total outstanding</span></div><strong className="metric-value">{formatCurrency(outstanding)}</strong><div className="collection-progress"><span>Outstanding / principal <b>{progress}%</b></span><div className="progress-track" role="progressbar" aria-label="Outstanding / principal" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><span style={{width:`${progress}%`}}/></div></div><p>of {formatCurrency(principal)} disbursed principal</p></div>
    <div className="summary-secondary"><div className="summary-metric"><div className="metric-label"><HandCoins size={17}/><span>Promises to pay</span></div><strong className="metric-value">{formatCurrency(ptp)}</strong><p><span className="metric-tag">{promises.length} recorded</span> payment promises</p></div><div className="summary-metric"><div className="metric-label"><Users size={17}/><span>Borrower accounts</span></div><strong className="metric-value">{customers.length}<span>borrowers</span></strong><p>{customers.length - settled} active <span className="metric-dot">·</span> {settled} settled</p></div><div className="summary-metric"><div className="metric-label"><PhoneCall size={17}/><span>Agent interactions</span></div><strong className="metric-value">{interactions.length}<span>calls</span></strong><p>{completed} completed <span className="metric-dot">·</span> {interactions.length ? Math.round(completed / interactions.length * 100) : 0}% connected</p></div></div>
  </section>
}

