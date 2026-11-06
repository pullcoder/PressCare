import { describe, expect, it } from 'vitest'
import { elapsedMinutes, formatElapsed, formatKstTime } from './time'

describe('경과 시간', () => {
  it('posture_since 부터 지금까지 분 단위', () => {
    const since = '2026-11-06T00:00:00Z'
    expect(elapsedMinutes(since, Date.parse('2026-11-06T02:05:59Z'))).toBe(125)
  })
  it('미래 시각이나 잘못된 값은 0', () => {
    expect(elapsedMinutes('2026-11-06T01:00:00Z', Date.parse('2026-11-06T00:00:00Z'))).toBe(0)
    expect(elapsedMinutes('nope', Date.now())).toBe(0)
  })
  it('표시 형식', () => {
    expect(formatElapsed(7)).toBe('7분')
    expect(formatElapsed(125)).toBe('2시간 05분')
  })
  it('한국 시간으로 표시', () => {
    expect(formatKstTime('2026-11-06T00:30:00Z')).toContain('09:30')
  })
})
