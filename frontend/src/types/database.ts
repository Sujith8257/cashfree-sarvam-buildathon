export interface Customer {
  customer_id: number
  name: string
  phone_number: string
  email: string | null
  language: string | null
  lending_date: string | null
  due_date: string | null
  outstanding_amount: number
  principal_amount: number
  interest_rate: number
}

export interface AgentInteraction {
  interaction_id: number
  customer_id: number
  call_datetime: string | null
  call_status: 'Completed' | 'Busy' | 'No Answer' | 'Failed' | 'Scheduled' | string | null
  language_used: string | null
  call_transcript: string | null
  call_summary: string | null
  customer_feedback: string | null
  payment_status: 'Promised to Pay' | 'Paid' | 'Refused' | 'Pending Review' | 'Disputed' | string | null
  promise_to_pay_date: string | null
  promise_to_pay_amount: number | null
  call_recording: string | null
  // Join helper
  customer?: Customer
}

export interface SupabaseConfig {
  url: string
  anonKey: string
  isConnected: boolean
}
