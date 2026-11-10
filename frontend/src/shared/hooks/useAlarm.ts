import { useCallback, useEffect, useRef, useState } from 'react'
import type { BedStatus } from '../constants/posture'

/** critical 병상이 하나라도 있으면 경고음을 반복한다. (D-012 1단계) */
export function shouldAlarm(statuses: BedStatus[]): boolean {
  return statuses.includes('critical')
}

function beep(ctx: AudioContext) {
  // 짧은 "삐-삐" 두 번. 소리 파일 없이 브라우저에서 만든다.
  for (const offset of [0, 0.35]) {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'square'
    osc.frequency.value = 880
    gain.gain.value = 0.08
    osc.connect(gain).connect(ctx.destination)
    osc.start(ctx.currentTime + offset)
    osc.stop(ctx.currentTime + offset + 0.2)
  }
}

/**
 * 브라우저는 사용자가 한 번 클릭해야 소리를 낼 수 있다 (SETUP 6장).
 * 그래서 "알림 소리 켜기" 버튼으로 enable() 을 불러야 한다.
 */
export function useAlarm(active: boolean, intervalMs = 2000) {
  const ctxRef = useRef<AudioContext | null>(null)
  const [enabled, setEnabled] = useState(false)

  const enable = useCallback(() => {
    ctxRef.current ??= new AudioContext()
    void ctxRef.current.resume()
    beep(ctxRef.current) // 켜졌다는 확인음
    setEnabled(true)
  }, [])

  const disable = useCallback(() => setEnabled(false), [])

  useEffect(() => {
    const ctx = ctxRef.current
    if (!enabled || !active || !ctx) return
    beep(ctx)
    const id = window.setInterval(() => beep(ctx), intervalMs)
    return () => window.clearInterval(id)
  }, [enabled, active, intervalMs])

  return { enabled, enable, disable }
}
