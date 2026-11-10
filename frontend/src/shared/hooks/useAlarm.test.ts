import { describe, expect, it } from 'vitest'
import { shouldAlarm } from './useAlarm'

describe('경고음 조건', () => {
  it('critical 이 하나라도 있으면 울린다', () => {
    expect(shouldAlarm(['ok', 'critical', 'warning'])).toBe(true)
  })
  it('warning 만 있으면 울리지 않는다', () => {
    expect(shouldAlarm(['ok', 'warning', 'unknown'])).toBe(false)
  })
})
