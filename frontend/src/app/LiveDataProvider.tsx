import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { getAlerts, getDevBeds, type DevAlert, type DevBedsResponse } from '../shared/api/devBeds'
import { LiveDataContext, type LiveData } from './liveDataContext'

/**
 * ⚠ 임시: 1초마다 backend 의 /dev/beds, /dev/alerts 를 읽어 모든 화면이 같이 쓴다.
 * Supabase 연결 후에는 bed_status·alerts Realtime 구독(T3-2)으로 바꾼다.
 */
export function LiveDataProvider({
  children,
  intervalMs = 1000,
}: {
  children: ReactNode
  intervalMs?: number
}) {
  const [source, setSource] = useState<LiveData['source']>('loading')
  const [beds, setBeds] = useState<DevBedsResponse | null>(null)
  const [alerts, setAlerts] = useState<DevAlert[]>([])
  const alive = useRef(true)

  const load = useCallback(async () => {
    try {
      const [b, a] = await Promise.all([getDevBeds(), getAlerts(50)])
      if (!alive.current) return
      setBeds(b)
      setAlerts(a)
      setSource('live')
    } catch {
      if (alive.current) setSource('unavailable')
    }
  }, [])

  useEffect(() => {
    alive.current = true
    const first = window.setTimeout(() => void load(), 0)
    const id = window.setInterval(() => void load(), intervalMs)
    return () => {
      alive.current = false
      window.clearTimeout(first)
      window.clearInterval(id)
    }
  }, [load, intervalMs])

  const value = useMemo<LiveData>(
    () => ({ source, beds, alerts, refresh: () => void load() }),
    [source, beds, alerts, load],
  )
  return <LiveDataContext.Provider value={value}>{children}</LiveDataContext.Provider>
}
