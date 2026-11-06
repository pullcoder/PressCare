import { POSTURE_LABEL, STATUS_LABEL, STATUS_STYLE } from '../../shared/constants/posture'
import { elapsedMinutes, formatElapsed, formatKstTime } from '../../shared/time'
import type { BedView } from './types'

type Props = { bed: BedView; now: number }

export function BedCard({ bed, now }: Props) {
  const minutes = elapsedMinutes(bed.postureSince, now)
  const showTimer = bed.status !== 'offline' && bed.posture !== 'absent'

  return (
    <article
      className={`rounded-xl border-2 p-4 shadow-sm ${STATUS_STYLE[bed.status]} ${
        bed.status === 'critical' ? 'animate-pulse' : ''
      }`}
    >
      <header className="flex items-baseline justify-between">
        <h3 className="text-lg font-bold">{bed.code}</h3>
        <span className="text-sm font-semibold">{STATUS_LABEL[bed.status]}</span>
      </header>
      <p className="mt-1 text-sm opacity-80">{bed.patientName ?? '환자 미배정'}</p>
      <p className="mt-3 text-base font-medium">{POSTURE_LABEL[bed.posture]}</p>
      {showTimer && (
        <p className="mt-1 text-2xl font-bold tabular-nums">
          {formatElapsed(minutes)}
          <span className="ml-2 text-xs font-normal opacity-70">
            {formatKstTime(bed.postureSince)}부터 유지
          </span>
        </p>
      )}
    </article>
  )
}
