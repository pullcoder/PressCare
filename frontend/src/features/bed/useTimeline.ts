import { useEffect, useState } from 'react'
import { getTimeline, type TimelineResponse } from '../../shared/api/devBeds'

/** 병상 하루 기록을 2초마다 다시 읽는다 (임시, Supabase 후에는 posture_events 조회). */
export function useTimeline(bedCode: string, intervalMs = 2000) {
  const [data, setData] = useState<TimelineResponse | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    const load = () =>
      getTimeline(bedCode)
        .then((d) => {
          if (!alive) return
          setData(d)
          setError(false)
        })
        .catch(() => alive && setError(true))
    void load()
    const id = window.setInterval(() => void load(), intervalMs)
    return () => {
      alive = false
      window.clearInterval(id)
    }
  }, [bedCode, intervalMs])

  return { data, error }
}
