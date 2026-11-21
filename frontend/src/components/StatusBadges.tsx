import React from 'react'
import { Badge } from './ui/badge'
import { CheckCircle2, Clock, XCircle, AlertCircle, PhoneCall, Calendar } from 'lucide-react'

export const CallStatusBadge: React.FC<{ status: string | null | undefined }> = ({ status }) => {
  if (!status) return <Badge variant="secondary">Unknown</Badge>

  switch (status.toLowerCase()) {
    case 'completed':
      return (
        <Badge variant="success" className="gap-1 font-medium">
          <CheckCircle2 className="h-3 w-3" /> Completed
        </Badge>
      )
    case 'busy':
      return (
        <Badge variant="warning" className="gap-1 font-medium">
          <Clock className="h-3 w-3" /> Busy
        </Badge>
      )
    case 'no answer':
    case 'no-answer':
      return (
        <Badge variant="secondary" className="gap-1 font-medium text-slate-600 dark:text-slate-400">
          <PhoneCall className="h-3 w-3 opacity-60" /> No Answer
        </Badge>
      )
    case 'failed':
      return (
        <Badge variant="danger" className="gap-1 font-medium">
          <XCircle className="h-3 w-3" /> Failed
        </Badge>
      )
    default:
      return <Badge variant="secondary">{status}</Badge>
  }
}

export const PaymentStatusBadge: React.FC<{ status: string | null | undefined }> = ({ status }) => {
  if (!status) return <Badge variant="secondary">Not Set</Badge>

  switch (status.toLowerCase()) {
    case 'promised to pay':
      return (
        <Badge variant="purple" className="gap-1 font-medium">
          <Calendar className="h-3 w-3" /> Promised to Pay
        </Badge>
      )
    case 'paid':
      return (
        <Badge variant="success" className="gap-1 font-medium">
          <CheckCircle2 className="h-3 w-3" /> Paid
        </Badge>
      )
    case 'disputed':
      return (
        <Badge variant="danger" className="gap-1 font-medium">
          <AlertCircle className="h-3 w-3" /> Disputed
        </Badge>
      )
    case 'refused':
      return (
        <Badge variant="danger" className="gap-1 font-medium">
          <XCircle className="h-3 w-3" /> Refused
        </Badge>
      )
    case 'pending review':
    default:
      return (
        <Badge variant="blue" className="gap-1 font-medium">
          <Clock className="h-3 w-3" /> {status}
        </Badge>
      )
  }
}
