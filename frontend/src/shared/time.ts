/** 경과 시간은 저장하지 않고 화면에서 `지금 - posture_since` 로 계산한다. (ARCHITECTURE 2장) */
export function elapsedMinutes(sinceIso: string, now: number): number {
  const since = Date.parse(sinceIso)
  if (Number.isNaN(since)) return 0
  return Math.max(0, Math.floor((now - since) / 60_000))
}

export function formatElapsed(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h > 0 ? `${h}시간 ${String(m).padStart(2, '0')}분` : `${m}분`
}

/** 화면 표시는 한국 시간 (DB 는 UTC) */
export function formatKstTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('ko-KR', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
  })
}
