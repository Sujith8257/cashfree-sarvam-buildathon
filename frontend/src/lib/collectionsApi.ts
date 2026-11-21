import { Customer } from '@/types/database'

// Served through the Vite proxy (vite.config.ts), which adds the API key and forces dry runs.
export interface QueueRow {
  rank?: number
  installment_id: string
  customer_id: string
  name: string
  due_date: string
  days_overdue: number
  outstanding_amount: number
  paid_amount: number
  status: string
  reason: string
}

export interface CallQueue {
  as_of: string
  call_queue: QueueRow[]
  other: QueueRow[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(path, init) } catch { throw new Error('Collections API unavailable') }
  if (!response.ok) throw new Error(`Collections API unavailable (HTTP ${response.status})`)
  try { return await response.json() as T } catch { throw new Error('Collections API unavailable') }
}

export async function fetchCallQueue(): Promise<CallQueue> {
  const queue = await request<CallQueue>('/api/queue')
  if (!Array.isArray(queue?.call_queue) || !Array.isArray(queue.other)) throw new Error('Collections API unavailable')
  return queue
}

export function addToCallQueue(customer: Customer): Promise<{ status: string; reason: string; installment_id?: string }> {
  return request('/api/trigger/call', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ customer_id: String(customer.customer_id), name: customer.name, phone_number: customer.phone_number, due_date: customer.due_date, outstanding_amount: customer.outstanding_amount }),
  })
}
