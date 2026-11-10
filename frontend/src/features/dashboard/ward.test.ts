import { describe, expect, it } from 'vitest'
import type { BedView } from './types'
import { groupByRoom, roomOf, sortBeds, summarize } from './ward'

const bed = (
  code: string,
  status: BedView['status'],
  elapsedMin = 0,
  needsCheck = false,
): BedView => ({
  bedId: code,
  code,
  patientName: null,
  posture: 'supine',
  postureSince: '2026-11-10T00:00:00Z',
  status,
  elapsedMin,
  needsCheck,
})

describe('병동 화면 정리', () => {
  it('병실 번호', () => {
    expect(roomOf('301-2')).toBe('301호')
    expect(roomOf('VIDEO-01')).toBe('기타 병상')
  })
  it('급한 순 정렬', () => {
    const beds = [
      bed('301-1', 'ok', 50),
      bed('301-2', 'critical', 130),
      bed('301-3', 'warning', 105),
      bed('301-4', 'ok', 20, true),
    ]
    expect(sortBeds(beds, 'urgent').map((b) => b.code)).toEqual([
      '301-2',
      '301-3',
      '301-4',
      '301-1',
    ])
    expect(sortBeds(beds, 'bed').map((b) => b.code)).toEqual(['301-1', '301-2', '301-3', '301-4'])
  })
  it('병실별 묶기와 요약', () => {
    const beds = [bed('301-1', 'ok'), bed('302-1', 'offline'), bed('301-2', 'unknown')]
    expect(groupByRoom(beds).map(([room, list]) => [room, list.length])).toEqual([
      ['301호', 2],
      ['302호', 1],
    ])
    expect(summarize(beds)).toEqual({ total: 3, critical: 0, warning: 0, check: 1, offline: 1 })
  })
})
