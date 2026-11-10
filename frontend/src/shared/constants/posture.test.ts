import { describe, expect, it } from 'vitest'
import { BED_STATUSES, POSTURE_LABEL, POSTURES, STATUS_LABEL, STATUS_STYLE } from './posture'

describe('자세·상태 표시', () => {
  it('모든 값에 한글 표시와 색이 있다', () => {
    for (const p of POSTURES) expect(POSTURE_LABEL[p]).toBeTruthy()
    for (const s of BED_STATUSES) {
      expect(STATUS_LABEL[s]).toBeTruthy()
      expect(STATUS_STYLE[s]).toBeTruthy()
    }
  })
  it('의료 판단 표현을 쓰지 않는다 (D-003)', () => {
    const text = [...Object.values(POSTURE_LABEL), ...Object.values(STATUS_LABEL)].join(' ')
    for (const word of ['진단', '예측', '위험', '확률']) expect(text).not.toContain(word)
  })
})
