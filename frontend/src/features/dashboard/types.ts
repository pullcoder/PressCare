import type { BedStatus, Posture } from '../../shared/constants/posture'

/** [x, y, visibility] 정규화 좌표 33개 (API.md). 영상이 아니라 숫자만 온다. */
export type Keypoints = number[][]

/** 대시보드 병상 카드 1개 (Supabase bed_status + beds + patients 를 합친 모양, API.md) */
export type BedView = {
  bedId: string
  code: string
  patientName: string | null // 화면에는 가명/이니셜만 (CONVENTIONS 6장)
  posture: Posture
  postureSince: string // ISO, UTC
  status: BedStatus
  elapsedMin?: number // 서버가 계산한 값(시연 가속 반영). 없으면 화면에서 계산
  keypoints?: Keypoints | null
  needsCheck?: boolean // 인식이 안 되는 중 → "확인 필요" 표시 (타이머는 계속)
  live?: boolean // 실제 병상이면 "체위변경 완료" 버튼 표시
}
