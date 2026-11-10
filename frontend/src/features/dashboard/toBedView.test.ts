import { describe, expect, it } from 'vitest'
import { toBedView } from './useLiveBeds'

describe('toBedView', () => {
  it('backend 병상 값을 카드 모양으로 바꾼다', () => {
    const view = toBedView({
      bed_code: '301-1',
      patient_name: '김○○',
      current_posture: 'left_lateral',
      confidence: 0.9,
      posture_since: '2026-11-06T09:00:00Z',
      status: 'warning',
      elapsed_min: 10.4,
      keypoints: null,
      needs_check: true,
      source: 'edge',
      simulated: false,
      alert: { id: 3, level: 'warning', acknowledged_by: null, acknowledged_at: null },
    })
    expect(view).toMatchObject({
      code: '301-1',
      patientName: '김○○',
      posture: 'left_lateral',
      elapsedMin: 10.4,
    })
    expect(view.needsCheck).toBe(true)
    expect(view.live).toBe(true)
    expect(view.alert?.id).toBe(3)
  })
})
