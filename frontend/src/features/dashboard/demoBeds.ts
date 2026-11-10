import type { BedView } from './types'

/**
 * Supabase 연결 전(T0-3) 화면 확인용 예시 데이터. 실제 환자 정보가 아니다.
 * 연결되면 useBedStatus(T3-2)가 이 자리를 대신한다.
 */
export function makeDemoBeds(now: number): BedView[] {
  const minutesAgo = (m: number) => new Date(now - m * 60_000).toISOString()
  return [
    {
      bedId: 'demo-1',
      code: '301-1',
      patientName: '김○○',
      posture: 'supine',
      postureSince: minutesAgo(35),
      status: 'ok',
    },
    {
      bedId: 'demo-2',
      code: '301-2',
      patientName: '이○○',
      posture: 'left_lateral',
      postureSince: minutesAgo(104),
      status: 'warning',
    },
    {
      bedId: 'demo-3',
      code: '301-3',
      patientName: '박○○',
      posture: 'right_lateral',
      postureSince: minutesAgo(127),
      status: 'critical',
    },
    {
      bedId: 'demo-4',
      code: '301-4',
      patientName: '최○○',
      posture: 'unknown',
      postureSince: minutesAgo(3),
      status: 'unknown',
    },
    {
      bedId: 'demo-5',
      code: '301-5',
      patientName: '정○○',
      posture: 'sitting',
      postureSince: minutesAgo(12),
      status: 'ok',
    },
    {
      bedId: 'demo-6',
      code: '301-6',
      patientName: null,
      posture: 'absent',
      postureSince: minutesAgo(50),
      status: 'offline',
    },
  ]
}
