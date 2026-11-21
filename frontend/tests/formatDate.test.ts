import assert from 'node:assert/strict'
import test from 'node:test'
import { formatDate } from '../src/lib/utils.ts'

test('formatDate keeps the calendar day of date-only values in every time zone', () => {
  for (const tz of ['America/Los_Angeles', 'Asia/Kolkata']) {
    process.env.TZ = tz
    assert.equal(formatDate('2026-11-24'), 'Nov 24, 2026', tz)
  }
})

test('formatDate still shows timestamps in the viewer time zone', () => {
  process.env.TZ = 'America/Los_Angeles'
  assert.equal(formatDate('2026-11-24T03:00:00Z'), 'Nov 23, 2026')
})
