import { useEffect, useState } from 'react'
import { getDevBeds, type DevBed } from '../../shared/api/devBeds'
import type { BedView } from './types'

export type LiveBeds =
  | { source: 'loading' }
  | { source: 'live'; beds: BedView[]; timeScale: number }
  | { source: 'unavailable' } // backend 가 꺼져 있거나 개발 모드가 아님 → 예시 데이터

export function toBedView(b: DevBed): BedView {
  return {
    bedId: b.bed_code,
    code: b.bed_code,
    patientName: null,
    posture: b.current_posture,
    postureSince: b.posture_since,
    status: b.status,
    elapsedMin: b.elapsed_min,
    keypoints: b.keypoints,
    needsCheck: b.needs_check,
    live: true,
  }
}

/** 임시: 1초마다 backend 의 /dev/beds 를 읽는다. Supabase 연결 후 Realtime 구독으로 교체. */
export function useLiveBeds(intervalMs = 1000): LiveBeds {
  const [state, setState] = useState<LiveBeds>({ source: 'loading' })

  useEffect(() => {
    let alive = true
    const load = () =>
      getDevBeds()
        .then((r) => {
          if (alive)
            setState({ source: 'live', beds: r.beds.map(toBedView), timeScale: r.time_scale })
        })
        .catch(() => {
          if (alive) setState({ source: 'unavailable' })
        })
    void load()
    const id = window.setInterval(() => void load(), intervalMs)
    return () => {
      alive = false
      window.clearInterval(id)
    }
  }, [intervalMs])

  return state
}
