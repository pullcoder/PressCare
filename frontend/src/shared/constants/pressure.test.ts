import { describe, expect, it } from 'vitest'
import { heatColor, PRESSURE_REGIONS, regionIntensities, regionMinutes } from './pressure'

describe('압박 부위 강도', () => {
  it('자세별 누적 시간으로 부위 강도를 계산한다', () => {
    const r = regionIntensities({ supine: 120, left_lateral: 240 }, 120)
    expect(r.sacrum).toBe(0.5) // 앙와위 120분 = 기준 1회
    expect(r.trochanter_left).toBe(1) // 좌측위 240분 = 기준 2회
    expect(r.trochanter_right).toBe(0)
  })
  it('앉음은 천골과 좌골 둘 다 누른다', () => {
    const r = regionIntensities({ sitting: 60, supine: 60 }, 120)
    expect(r.sacrum).toBe(0.5)
    expect(r.ischium).toBe(0.25)
  })
  it('키가 겹치지 않는다', () => {
    const keys = PRESSURE_REGIONS.map((x) => x.key)
    expect(new Set(keys).size).toBe(keys.length)
  })
  it('색은 회색 → 주황 → 빨강', () => {
    expect(heatColor(0)).toBe('rgb(209, 213, 219)')
    expect(heatColor(0.5)).toBe('rgb(245, 158, 11)')
    expect(heatColor(2)).toBe('rgb(220, 38, 38)')
  })
})

describe('부위별 누적 시간', () => {
  it('부위를 누르는 자세들의 시간을 더한다', () => {
    const m = regionMinutes({ supine: 30, sitting: 20 })
    expect(m.sacrum).toBe(50)
    expect(m.heel_left).toBe(30)
    expect(m.ear_left).toBe(0)
  })
})
