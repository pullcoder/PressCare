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
