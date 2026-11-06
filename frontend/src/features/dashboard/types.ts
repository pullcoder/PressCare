import type { BedStatus, Posture } from '../../shared/constants/posture'

/** 대시보드 병상 카드 1개 (Supabase bed_status + beds + patients 를 합친 모양, API.md) */
export type BedView = {
  bedId: string
  code: string
  patientName: string | null // 화면에는 가명/이니셜만 (CONVENTIONS 6장)
  posture: Posture
  postureSince: string // ISO, UTC
  status: BedStatus
}
