import { useEffect, useState } from 'react'

/** intervalMs 마다 현재 시각(ms)을 갱신한다. 경과 시간 표시용. */
export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(id)
  }, [intervalMs])
  return now
}
