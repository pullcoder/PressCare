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

/** 카드에 쓰는 "다음 체위변경까지" 문구. 시간은 시연 가속이 반영된 분 단위. */
export function formatRemaining(elapsedMin: number, intervalMin: number): string {
  const left = Math.round(intervalMin - elapsedMin)
  if (left > 0) return `다음 체위변경까지 ${formatElapsed(left)}`
  if (left === 0) return '지금 체위변경 시간'
  return `기준 시간 ${formatElapsed(-left)} 초과`
}
