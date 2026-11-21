import test from 'node:test'
import assert from 'node:assert/strict'
import { parseCsv, validateBorrowerCsv } from '../src/lib/borrowerCsv.ts'

test('handles BOM, CRLF, quoted commas, escaped quotes and embedded newlines', () => {
  assert.deepEqual(parseCsv('\uFEFFname,note\r\n"Doe, Jane","said ""yes""\nnext"\r\n'), [['name', 'note'], ['Doe, Jane', 'said "yes"\nnext']])
})
test('validates required fields and uses principal as the default outstanding amount', () => {
  const result = validateBorrowerCsv('name,phone_number,principal_amount\nJane,+919876543210,1200')
  assert.equal(result.errors.length, 0)
  assert.equal(result.borrowers[0].outstanding_amount, 1200)
  assert.equal(result.borrowers[0].interest_rate, 0)
})
test('reports invalid dates, amounts and column counts with row numbers', () => {
  const result = validateBorrowerCsv('name,phone_number,principal_amount,due_date\nJane,9876543210,1200,2026-02-30\nJoe,9876543210,-5,\nSam,9876543210')
  assert.equal(result.errors.length, 3)
  assert.match(result.errors[0], /Row 2/)
  assert.equal(result.borrowers.length, 0)
})
test('rejects malformed quotes, duplicate headers and missing columns', () => {
  assert.throws(() => parseCsv('name\n"unclosed'))
  assert.throws(() => validateBorrowerCsv('name,name\nA,B'), /duplicate/)
  assert.throws(() => validateBorrowerCsv('name\nJane'), /phone_number/)
})
test('round trips exported borrower columns without importing IDs', () => {
  const result = validateBorrowerCsv('customer_id,name,phone_number,email,language,lending_date,due_date,principal_amount,outstanding_amount,interest_rate\n123,Jane,9876543210,,Kannada,2026-01-01,2026-02-01,1200,0,2')
  assert.equal(result.errors.length, 0)
  assert.equal(result.borrowers[0].outstanding_amount, 0)
  assert.equal('customer_id' in result.borrowers[0], false)
})
