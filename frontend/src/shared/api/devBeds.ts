import type { BedStatus, Posture } from '../constants/posture'
import { apiRequest } from './client'

/** ⚠ 임시: Supabase 준비 전 개발 모드 API (API.md 3장). 연결되면 Realtime 구독(T3-2)으로 바꾼다. */
export type DevBed = {
  bed_code: string
  current_posture: Posture
  confidence: number
  posture_since: string
  status: BedStatus
  elapsed_min: number
  keypoints: number[][] | null
  needs_check: boolean // 지금 인식이 안 됨 (마지막 자세·타이머는 유지)
  source: 'edge' | 'manual'
}

export type DevBedsResponse = {
  time_scale: number
  reposition_warning_min: number
  reposition_interval_min: number
  beds: DevBed[]
}

export function getDevBeds(): Promise<DevBedsResponse> {
  return apiRequest<DevBedsResponse>('/dev/beds')
}

/** 간호사 "체위변경 완료" (임시 경로. 원래는 POST /beds/{bed_id}/postures/manual, 로그인 필요) */
export function recordManualPosture(bedCode: string, posture: Posture): Promise<{ ok: boolean }> {
  return apiRequest<{ ok: boolean }>(`/dev/beds/${encodeURIComponent(bedCode)}/postures/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ posture }),
  })
}
