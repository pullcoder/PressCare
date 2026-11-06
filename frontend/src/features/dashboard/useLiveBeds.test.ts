import { describe, expect, it } from 'vitest'
import { toBedView } from './useLiveBeds'

describe('toBedView', () => {
  it('backend 병상 값을 카드 모양으로 바꾼다', () => {
    const view = toBedView({
      bed_code: 'BED-01',
      current_posture: 'left_lateral',
      confidence: 0.9,
      posture_since: '2026-11-06T09:00:00Z',
      status: 'warning',
      elapsed_min: 10.4,
      keypoints: null,
    })
    expect(view).toMatchObject({
      code: 'BED-01',
      posture: 'left_lateral',
      status: 'warning',
      elapsedMin: 10.4,
    })
    expect(view.patientName).toBeNull()
  })
})
