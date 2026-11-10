/**
 * 자세·상태 값과 한글 표시는 여기 한 곳에서만 정의한다. (CONVENTIONS 2장)
 * 의료 판단 표현(진단·예측·위험·확률)은 쓰지 않는다. (D-003)
 */

export const POSTURES = [
  'supine',
  'left_lateral',
  'right_lateral',
  'sitting',
  'absent',
  'unknown',
] as const
export type Posture = (typeof POSTURES)[number]

export const POSTURE_LABEL: Record<Posture, string> = {
  supine: '바로 누움',
  left_lateral: '왼쪽으로 누움',
  right_lateral: '오른쪽으로 누움',
  sitting: '앉음',
  absent: '자리 비움',
  unknown: '확인 필요',
}

export const BED_STATUSES = ['ok', 'warning', 'critical', 'unknown', 'offline'] as const
export type BedStatus = (typeof BED_STATUSES)[number]

export const STATUS_LABEL: Record<BedStatus, string> = {
  ok: '정상',
  warning: '체위변경 곧 필요',
  critical: '체위변경 필요',
  unknown: '확인 필요',
  offline: '연결 끊김',
}

/** 상태 색은 의미로 고정: ok 초록, warning 노랑, critical 빨강, unknown/offline 회색 */
export const STATUS_STYLE: Record<BedStatus, string> = {
  ok: 'border-green-500 bg-green-50 text-green-900',
  warning: 'border-yellow-500 bg-yellow-50 text-yellow-900',
  critical: 'border-red-600 bg-red-50 text-red-900',
  unknown: 'border-gray-400 bg-gray-50 text-gray-700',
  offline: 'border-gray-400 bg-gray-100 text-gray-500',
}

/** 타임라인 막대 색 (자세 구분용, 상태 색과 겹치지 않게) */
export const POSTURE_COLOR: Record<Posture, string> = {
  supine: '#3b82f6',
  left_lateral: '#14b8a6',
  right_lateral: '#8b5cf6',
  sitting: '#f59e0b',
  absent: '#9ca3af',
  unknown: '#d1d5db',
}
