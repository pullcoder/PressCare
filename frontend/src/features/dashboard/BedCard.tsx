import { Link } from 'react-router-dom'
import { POSTURE_LABEL, STATUS_LABEL, STATUS_STYLE } from '../../shared/constants/posture'
import { elapsedMinutes, formatElapsed, formatKstTime, formatRemaining } from '../../shared/time'
import { RepositionButton } from './RepositionButton'
import { SkeletonView } from './SkeletonView'
import type { BedView } from './types'

type Props = { bed: BedView; now: number; intervalMin: number }

export function BedCard({ bed, now, intervalMin }: Props) {
  const minutes =
    bed.elapsedMin !== undefined
      ? Math.floor(bed.elapsedMin)
      : elapsedMinutes(bed.postureSince, now)
  const offline = bed.status === 'offline'
  const showTimer = !offline && bed.posture !== 'absent' && bed.posture !== 'unknown'
  const urgent = bed.status === 'warning' || bed.status === 'critical'
  const alert = bed.alert

  const title = (
    <span className="text-lg font-bold">
      {bed.code}
      {bed.live && <span className="ml-1 text-sm font-normal opacity-60">›</span>}
    </span>
  )

  return (
    <article
      className={`flex flex-col rounded-xl border-2 p-4 shadow-sm ${STATUS_STYLE[bed.status]} ${
        bed.status === 'critical' && !alert?.acknowledged_at ? 'animate-pulse' : ''
      }`}
    >
      <header className="flex items-baseline justify-between gap-2">
        {bed.live ? (
          <Link to={`/beds/${encodeURIComponent(bed.code)}`} className="hover:underline">
            {title}
          </Link>
        ) : (
          title
        )}
        <span className="text-sm font-semibold">{STATUS_LABEL[bed.status]}</span>
      </header>
      <p className="mt-0.5 text-sm opacity-80">
        {bed.patientName ?? '환자 정보 없음'}
        {bed.live && !bed.simulated && (
          <span className="ml-2 rounded bg-teal-700 px-1.5 py-0.5 text-[10px] font-semibold text-white">
            카메라 연결
          </span>
        )}
      </p>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {bed.needsCheck && (
          <span className="rounded bg-gray-800 px-2 py-0.5 text-xs font-semibold text-white">
            인식 안 됨 · 타이머 유지
          </span>
        )}
        {alert && !alert.acknowledged_at && (
          <span
            className={`rounded px-2 py-0.5 text-xs font-semibold ${
              alert.level === 'critical' ? 'bg-red-700 text-white' : 'bg-yellow-400 text-yellow-950'
            }`}
          >
            미확인 알림
          </span>
        )}
        {alert?.acknowledged_at && (
          <span className="rounded bg-white/80 px-2 py-0.5 text-xs text-gray-700 ring-1 ring-black/10">
            확인됨 · {alert.acknowledged_by} {formatKstTime(alert.acknowledged_at)}
          </span>
        )}
      </div>

      <div className="mt-2 flex flex-1 items-end justify-between gap-3">
        <div>
          <p className="text-base font-medium">
            {offline ? '카메라 연결 끊김' : POSTURE_LABEL[bed.posture]}
          </p>
          {showTimer && (
            <>
              <p className="mt-0.5 text-2xl font-bold tabular-nums">
                {formatElapsed(minutes)}
                <span className="ml-2 text-xs font-normal opacity-70">
                  {formatKstTime(bed.postureSince)}부터 유지
                </span>
              </p>
              <p className={`text-xs ${urgent ? 'font-semibold' : 'opacity-70'}`}>
                {formatRemaining(minutes, intervalMin)}
              </p>
            </>
          )}
          {offline && <p className="text-xs opacity-70">엣지 PC·카메라를 확인하세요</p>}
        </div>
        {bed.keypoints && <SkeletonView keypoints={bed.keypoints} />}
      </div>

      {bed.live && !offline && (
        <RepositionButton bedCode={bed.code} prominent={urgent || Boolean(bed.needsCheck)} />
      )}
    </article>
  )
}
