import type { BedStatus } from '../../shared/constants/posture'
import type { BedView } from './types'

/** "301-2" → "301호". 형식이 다르면 "기타 병상". */
export function roomOf(code: string): string {
  const m = /^(\d{3,4})-\d+$/.exec(code)
  return m ? `${m[1]}호` : '기타 병상'
}

const URGENCY: Record<BedStatus, number> = {
  critical: 0,
  warning: 1,
  unknown: 2,
  offline: 3,
  ok: 4,
}

export type SortMode = 'urgent' | 'bed'

/** 급한 순: 체위변경 필요 → 곧 필요 → 확인 필요 → 연결 끊김 → 정상, 같으면 오래된 순 */
export function sortBeds(beds: BedView[], mode: SortMode): BedView[] {
  const copy = [...beds]
  if (mode === 'bed')
    return copy.sort((a, b) => a.code.localeCompare(b.code, 'ko', { numeric: true }))
  return copy.sort((a, b) => {
    const ua = a.needsCheck && a.status === 'ok' ? URGENCY.unknown : URGENCY[a.status]
    const ub = b.needsCheck && b.status === 'ok' ? URGENCY.unknown : URGENCY[b.status]
    if (ua !== ub) return ua - ub
    return (b.elapsedMin ?? 0) - (a.elapsedMin ?? 0)
  })
}

export function groupByRoom(beds: BedView[]): [string, BedView[]][] {
  const map = new Map<string, BedView[]>()
  for (const b of beds) {
    const room = roomOf(b.code)
    map.set(room, [...(map.get(room) ?? []), b])
  }
  return [...map.entries()]
}

export type WardSummary = Record<'total' | 'critical' | 'warning' | 'check' | 'offline', number>

export function summarize(beds: BedView[]): WardSummary {
  return {
    total: beds.length,
    critical: beds.filter((b) => b.status === 'critical').length,
    warning: beds.filter((b) => b.status === 'warning').length,
    check: beds.filter((b) => b.status === 'unknown' || b.needsCheck).length,
    offline: beds.filter((b) => b.status === 'offline').length,
  }
}
