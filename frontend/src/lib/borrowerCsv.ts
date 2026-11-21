import type { Customer } from '@/types/database'

export type NewBorrower = Omit<Customer, 'customer_id'>
export const CSV_HEADERS = ['name', 'phone_number', 'email', 'language', 'lending_date', 'due_date', 'principal_amount', 'outstanding_amount', 'interest_rate']

// Parse quoted fields, escaped quotes, embedded newlines, CRLF and UTF-8 BOM.
export function parseCsv(text: string): string[][] {
  const rows: string[][] = []; let row: string[] = []; let field = ''; let quoted = false; let closed = false
  text = text.replace(/^\uFEFF/, '')
  for (let i = 0; i < text.length; i++) {
    const char = text[i]
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') { field += '"'; i++ }
      else if (char === '"') { quoted = false; closed = true }
      else field += char
    } else if (char === ',' || char === '\n' || char === '\r') {
      row.push(field); field = ''; closed = false
      if (char !== ',') { if (row.some(value => value.trim())) rows.push(row); row = []; if (char === '\r' && text[i + 1] === '\n') i++ }
    } else if (char === '"') {
      if (field || closed) throw new Error('Invalid quotation in CSV. Use the downloadable template.')
      quoted = true
    } else {
      if (closed) throw new Error('Unexpected text after a quoted field.')
      field += char
    }
  }
  if (quoted) throw new Error('A quoted field is missing its closing quote.')
  row.push(field); if (row.some(value => value.trim())) rows.push(row)
  return rows
}

export function validateBorrowerCsv(text: string): { borrowers: NewBorrower[]; errors: string[] } {
  const rows = parseCsv(text)
  if (rows.length < 2) throw new Error('Include a header and at least one borrower.')
  if (rows.length > 1001) throw new Error('Import up to 1,000 borrowers at a time.')
  const headers = rows[0].map(value => value.trim().toLowerCase())
  if (new Set(headers).size !== headers.length) throw new Error('CSV contains duplicate column headers.')
  for (const required of ['name', 'phone_number', 'principal_amount']) {
    if (!headers.includes(required)) throw new Error(`Missing required column: ${required}`)
  }
  const borrowers: NewBorrower[] = []; const errors: string[] = []
  rows.slice(1).forEach((values, index) => {
    try {
      if (values.length !== headers.length) throw new Error('Column count does not match the header.')
      const data = Object.fromEntries(headers.map((key, i) => [key, values[i].trim()]))
      if (!data.name) throw new Error('Name is required.')
      if (!/^\+?[\d ()-]{7,20}$/.test(data.phone_number) || data.phone_number.replace(/\D/g, '').length < 7) throw new Error('Enter a valid phone number.')
      if (data.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) throw new Error('Email is invalid.')
      const number = (key: string, fallback?: number) => {
        const value = data[key]
        if (!value && fallback !== undefined) return fallback
        if (!value || !/^\d+(\.\d+)?$/.test(value) || !Number.isFinite(Number(value))) throw new Error(`${key} must be a non-negative number without currency symbols or commas.`)
        return Number(value)
      }
      const date = (key: string) => {
        const value = data[key]
        if (!value) return null
        const parsed = new Date(value)
        if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) throw new Error(`${key} must be a valid YYYY-MM-DD date.`)
        return value
      }
      const principal = number('principal_amount'); const lending = date('lending_date'); const due = date('due_date')
      if (lending && due && due < lending) throw new Error('Due date must be on or after lending date.')
      borrowers.push({ name: data.name, phone_number: data.phone_number, email: data.email || null, language: data.language || 'English', lending_date: lending, due_date: due, principal_amount: principal, outstanding_amount: number('outstanding_amount', principal), interest_rate: number('interest_rate', 0) })
    } catch (error) { errors.push(`Row ${index + 2}: ${error instanceof Error ? error.message : 'Invalid record.'}`) }
  })
  return { borrowers, errors }
}
