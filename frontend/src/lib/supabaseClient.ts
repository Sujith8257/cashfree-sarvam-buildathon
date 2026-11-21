import { createClient, SupabaseClient } from '@supabase/supabase-js'
import { Customer, AgentInteraction } from '@/types/database'
import { INITIAL_CUSTOMERS, INITIAL_INTERACTIONS } from '@/data/mockData'

const LOCAL_STORAGE_KEY_URL = 'cashfree_supabase_url'
const LOCAL_STORAGE_KEY_KEY = 'cashfree_supabase_anon_key'

export function getStoredSupabaseConfig() {
  const envUrl = import.meta.env.VITE_SUPABASE_URL || ''
  const envKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

  const storedUrl = localStorage.getItem(LOCAL_STORAGE_KEY_URL) || envUrl
  const storedKey = localStorage.getItem(LOCAL_STORAGE_KEY_KEY) || envKey

  return {
    url: storedUrl,
    anonKey: storedKey,
    hasCredentials: Boolean(storedUrl && storedKey),
  }
}

export function saveSupabaseConfig(url: string, anonKey: string) {
  if (url) localStorage.setItem(LOCAL_STORAGE_KEY_URL, url.trim())
  else localStorage.removeItem(LOCAL_STORAGE_KEY_URL)

  if (anonKey) localStorage.setItem(LOCAL_STORAGE_KEY_KEY, anonKey.trim())
  else localStorage.removeItem(LOCAL_STORAGE_KEY_KEY)
}

let cachedClient: SupabaseClient | null = null
let currentConfig = ''

export function getSupabaseClient(): SupabaseClient | null {
  const { url, anonKey, hasCredentials } = getStoredSupabaseConfig()
  if (!hasCredentials) return null

  const configSignature = `${url}:${anonKey}`
  if (cachedClient && currentConfig === configSignature) {
    return cachedClient
  }

  try {
    cachedClient = createClient(url, anonKey)
    currentConfig = configSignature
    return cachedClient
  } catch (err) {
    console.error('Failed to initialize Supabase client:', err)
    return null
  }
}

// Data fetching helper
export async function fetchCustomersData(): Promise<{ data: Customer[]; isLive: boolean; error?: string }> {
  const client = getSupabaseClient()
  if (!client) {
    return { data: getLocalCustomers(), isLive: false }
  }

  try {
    const { data, error } = await client
      .from('customers')
      .select('*')
      .order('customer_id', { ascending: true })

    if (error) {
      console.warn('Supabase query error (falling back to local cache):', error.message)
      return { data: [], isLive: false, error: error.message }
    }

    if (data && data.length > 0) {
      return { data: data as Customer[], isLive: true }
    }

    return { data: [], isLive: true }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return { data: [], isLive: false, error: msg }
  }
}

export async function fetchInteractionsData(): Promise<{ data: AgentInteraction[]; isLive: boolean; error?: string }> {
  const client = getSupabaseClient()
  if (!client) {
    return { data: getLocalInteractions(), isLive: false }
  }

  try {
    const { data, error } = await client
      .from('agent')
      .select('*')
      .order('call_datetime', { ascending: false })

    if (error) {
      console.warn('Supabase query error (falling back to local cache):', error.message)
      return { data: [], isLive: false, error: error.message }
    }

    if (data && data.length > 0) {
      return { data: data as AgentInteraction[], isLive: true }
    }

    return { data: [], isLive: true }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return { data: [], isLive: false, error: msg }
  }
}

// Local storage state fallbacks
const CUSTOMERS_LOCAL_STORAGE = 'cashfree_local_customers'
const INTERACTIONS_LOCAL_STORAGE = 'cashfree_local_interactions'

export function getLocalCustomers(): Customer[] {
  try {
    const raw = localStorage.getItem(CUSTOMERS_LOCAL_STORAGE)
    if (raw) return JSON.parse(raw)
  } catch {}
  return INITIAL_CUSTOMERS
}

export function saveLocalCustomers(customers: Customer[]) {
  localStorage.setItem(CUSTOMERS_LOCAL_STORAGE, JSON.stringify(customers))
}

export function getLocalInteractions(): AgentInteraction[] {
  try {
    const raw = localStorage.getItem(INTERACTIONS_LOCAL_STORAGE)
    if (raw) return JSON.parse(raw)
  } catch {}
  return INITIAL_INTERACTIONS
}

export function saveLocalInteractions(interactions: AgentInteraction[]) {
  localStorage.setItem(INTERACTIONS_LOCAL_STORAGE, JSON.stringify(interactions))
}

// Create new interaction
export async function addInteraction(interaction: Omit<AgentInteraction, 'interaction_id'>): Promise<{ success: boolean; data?: AgentInteraction; error?: string; storage?: 'supabase' | 'local' }> {
  const client = getSupabaseClient()
  let saveError: string | undefined = !client && getStoredSupabaseConfig().hasCredentials ? 'Could not connect to Supabase.' : undefined
  if (client) {
    try {
      const { data, error } = await client
        .from('agent')
        .insert([interaction])
        .select()
        .single()

      if (!error && data) {
        return { success: true, data, storage: 'supabase' }
      }
      saveError = error?.message || 'Supabase did not return the saved record.'
      return { success: false, storage: 'supabase', error: error?.message || 'Could not save record to Supabase.' }
    } catch (err) {
      return { success: false, storage: 'supabase', error: err instanceof Error ? err.message : 'Could not save interaction.' }
    }
  }

  // Fallback local save
  const existing = getLocalInteractions()
  const newId = existing.length > 0 ? Math.max(...existing.map(i => i.interaction_id)) + 1 : 1
  const newRecord: AgentInteraction = {
    ...interaction,
    interaction_id: newId,
  }
  const updated = [newRecord, ...existing]
  saveLocalInteractions(updated)
  return { success: true, data: newRecord, storage: 'local', error: saveError }
}

// Create new customer
export async function addCustomer(customer: Omit<Customer, 'customer_id'>): Promise<{ success: boolean; data?: Customer; error?: string; storage?: 'supabase' | 'local' }> {
  const client = getSupabaseClient()
  let saveError: string | undefined = !client && getStoredSupabaseConfig().hasCredentials ? 'Could not connect to Supabase.' : undefined
  if (client) {
    try {
      const { data, error } = await client
        .from('customers')
        .insert([customer])
        .select()
        .single()

      if (!error && data) {
        return { success: true, data, storage: 'supabase' }
      }
      saveError = error?.message || 'Supabase did not return the saved record.'
      return { success: false, storage: 'supabase', error: error?.message || 'Could not save record to Supabase.' }
    } catch (err) {
      return { success: false, storage: 'supabase', error: err instanceof Error ? err.message : 'Could not save customer.' }
    }
  }

  const existing = getLocalCustomers()
  const newId = existing.length > 0 ? Math.max(...existing.map(c => c.customer_id)) + 1 : 101
  const newRecord: Customer = {
    ...customer,
    customer_id: newId,
  }
  const updated = [...existing, newRecord]
  saveLocalCustomers(updated)
  return { success: true, data: newRecord, storage: 'local', error: saveError }
}



// One insert keeps a CSV batch atomic; never fall back to local data after a live failure.
export async function importCustomers(customers: Omit<Customer, 'customer_id'>[]): Promise<Customer[]> {
  if (!customers.length || customers.length > 1000) throw new Error('Import between 1 and 1,000 borrowers.')
  const client = getSupabaseClient()
  if (client) {
    const { data, error } = await client.from('customers').insert(customers).select()
    if (error) throw new Error(error.message)
    return (data || []) as Customer[]
  }
  if (getStoredSupabaseConfig().hasCredentials) throw new Error('Could not connect to Supabase. Check your connection and retry.')
  const existing = getLocalCustomers()
  const firstId = existing.length ? Math.max(...existing.map(customer => customer.customer_id)) + 1 : 101
  const records = customers.map((customer, index) => ({ ...customer, customer_id: firstId + index }))
  saveLocalCustomers([...existing, ...records])
  return records
}
