import type { BedStatus, Posture } from '../constants/posture'
import { apiRequest } from './client'

/**
 * ⚠ 임시: Supabase 준비 전 개발 모드 API (API.md 3장).
 * 연결되면 bed_status·posture_events·alerts 를 Supabase 에서 직접 읽고 Realtime 구독(T3-2)으로 바꾼다.
 */
export type DevAlertBrief = {
  id: number
  level: BedStatus
  acknowledged_by: string | null
  acknowledged_at: string | null
}

export type DevBed = {
  bed_code: string
  patient_name: string | null
  current_posture: Posture
  confidence: number
  posture_since: string
  status: BedStatus
  elapsed_min: number
  keypoints: number[][] | null
  needs_check: boolean // 지금 인식이 안 됨 (마지막 자세·타이머는 유지)
  source: 'edge' | 'manual'
  simulated: boolean // 시연용 가짜 병상
  alert: DevAlertBrief | null
}

export type DevBedsResponse = {
  time_scale: number
  reposition_warning_min: number
  reposition_interval_min: number
  beds: DevBed[]
}

export type TimelineEvent = {
  posture: Posture
  started_at: string
  ended_at: string | null
  duration_min: number
  source: 'edge' | 'manual'
  recorded_by: string | null
}

export type TimelineResponse = {
  bed_code: string
  patient_name: string | null
  time_scale: number
  reposition_interval_min: number
  events: TimelineEvent[]
  totals_min: Partial<Record<Posture, number>>
  reposition_count: number
  longest_min: number
}

export type DevAlert = {
  id: number
  bed_code: string
  patient_name: string | null
  level: BedStatus
  created_at: string
  acknowledged_at: string | null
  acknowledged_by: string | null
  resolved_at: string | null
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export function getDevBeds(): Promise<DevBedsResponse> {
  return apiRequest<DevBedsResponse>('/dev/beds')
}

export function getTimeline(bedCode: string): Promise<TimelineResponse> {
  return apiRequest<TimelineResponse>(`/dev/beds/${encodeURIComponent(bedCode)}/timeline`)
}

/** 간호사 수동 기록·보정 (임시 경로. 원래는 POST /beds/{bed_id}/postures/manual, 로그인 필요) */
export function recordManualPosture(
  bedCode: string,
  posture: Posture,
  recordedBy?: string,
): Promise<{ ok: boolean }> {
  return apiRequest<{ ok: boolean }>(
    `/dev/beds/${encodeURIComponent(bedCode)}/postures/manual`,
    json({ posture, recorded_by: recordedBy }),
  )
}

export function getAlerts(limit = 50): Promise<DevAlert[]> {
  return apiRequest<DevAlert[]>(`/dev/alerts?limit=${limit}`)
}

export function ackAlert(id: number, by: string): Promise<DevAlert> {
  return apiRequest<DevAlert>(`/dev/alerts/${id}/ack`, json({ acknowledged_by: by }))
}
