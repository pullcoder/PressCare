import { lazy, Suspense, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  POSTURE_COLOR,
  POSTURE_LABEL,
  STATUS_LABEL,
  STATUS_STYLE,
} from '../../shared/constants/posture'
import {
  heatColor,
  PRESSURE_REGIONS,
  regionIntensities,
  regionMinutes,
} from '../../shared/constants/pressure'
import { formatElapsed, formatKstTime, formatRemaining } from '../../shared/time'
import { RepositionButton } from '../dashboard/RepositionButton'
import { toBedView, useLiveData } from '../dashboard/useLiveBeds'
import { useTimeline } from './useTimeline'

const Heatmap3D = lazy(() => import('./Heatmap3D'))

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white px-4 py-3 shadow-sm">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-0.5 text-xl font-bold tabular-nums">{value}</p>
    </div>
  )
}

/** 병상 상세: 현재 상태, 오늘 자세 기록(타임라인), 3D 압박 부위 (T3-5, F4) */
export default function BedDetailPage() {
  const { code = '' } = useParams()
  const live = useLiveData()
  const { data, error } = useTimeline(code)
  const raw = live.beds?.beds.find((b) => b.bed_code === code)
  const bed = raw ? toBedView(raw) : null
  const intervalMin = live.beds?.reposition_interval_min ?? 120
  const scale = live.beds?.time_scale ?? 1

  const intensities = useMemo(
    () => regionIntensities(data?.totals_min ?? {}, data?.reposition_interval_min ?? intervalMin),
    [data, intervalMin],
  )
  const minutesByRegion = regionMinutes(data?.totals_min ?? {})
  const ranked = [...PRESSURE_REGIONS]
    .map((r) => ({ ...r, value: intensities[r.key] ?? 0, minutes: minutesByRegion[r.key] ?? 0 }))
    .filter((r) => r.value > 0)
    .sort((a, b) => b.value - a.value)
  const events = data?.events ?? []
  const totalMin = events.reduce((s, e) => s + e.duration_min, 0) || 1

  if (live.source === 'unavailable') {
    return <p className="text-sm text-gray-600">백엔드가 꺼져 있어 병상 정보를 볼 수 없습니다.</p>
  }
  if (live.source === 'live' && !bed) {
    return (
      <p className="text-sm text-gray-600">
        병상 {code}을(를) 찾을 수 없습니다.{' '}
        <Link to="/" className="underline">
          대시보드로
        </Link>
      </p>
    )
  }

  return (
    <div className="space-y-5">
      <Link to="/" className="text-sm text-teal-700 hover:underline">
        ‹ 대시보드
      </Link>

      {bed && (
        <section className={`rounded-xl border-2 p-5 ${STATUS_STYLE[bed.status]}`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold">
                {bed.code} <span className="text-lg font-normal">{bed.patientName ?? ''}</span>
              </h2>
              <p className="mt-1 text-lg font-medium">
                {POSTURE_LABEL[bed.posture]} · {formatElapsed(Math.floor(bed.elapsedMin ?? 0))} 유지
              </p>
              <p className="text-sm opacity-80">
                {formatRemaining(Math.floor(bed.elapsedMin ?? 0), intervalMin)}
              </p>
            </div>
            <span className="rounded-full bg-white/80 px-3 py-1 text-sm font-bold">
              {STATUS_LABEL[bed.status]}
            </span>
          </div>
          <div className="max-w-xs">
            <RepositionButton
              bedCode={bed.code}
              prominent={
                bed.status === 'warning' || bed.status === 'critical' || Boolean(bed.needsCheck)
              }
            />
          </div>
        </section>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="오늘 체위변경" value={`${data?.reposition_count ?? 0}회`} />
        <Stat label="가장 오래 유지" value={formatElapsed(Math.floor(data?.longest_min ?? 0))} />
        <Stat label="기준 시간" value={formatElapsed(intervalMin)} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="space-y-3 rounded-xl bg-white p-4 shadow-sm">
          <h3 className="font-bold">오늘 자세 기록</h3>
          {error && <p className="text-sm text-red-700">기록을 불러오지 못했습니다.</p>}
          <div
            className="flex h-6 overflow-hidden rounded-md ring-1 ring-gray-200"
            aria-label="자세 유지 막대"
          >
            {events.map((e) => (
              <div
                key={e.started_at}
                title={`${POSTURE_LABEL[e.posture]} ${formatElapsed(Math.floor(e.duration_min))}`}
                style={{
                  width: `${(e.duration_min / totalMin) * 100}%`,
                  background: POSTURE_COLOR[e.posture],
                }}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-gray-600">
            {(['supine', 'left_lateral', 'right_lateral', 'sitting'] as const).map((p) => (
              <span key={p} className="flex items-center gap-1">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-sm"
                  style={{ background: POSTURE_COLOR[p] }}
                />
                {POSTURE_LABEL[p]}
              </span>
            ))}
          </div>
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-gray-500">
              <tr>
                <th className="py-1">시작</th>
                <th>자세</th>
                <th>유지</th>
                <th>기록</th>
              </tr>
            </thead>
            <tbody>
              {[...events].reverse().map((e) => (
                <tr key={e.started_at} className="border-t border-gray-100">
                  <td className="py-1.5 tabular-nums">{formatKstTime(e.started_at)}</td>
                  <td>{POSTURE_LABEL[e.posture]}</td>
                  <td className="tabular-nums">
                    {formatElapsed(Math.floor(e.duration_min))}
                    {!e.ended_at && <span className="ml-1 text-xs text-teal-700">진행 중</span>}
                  </td>
                  <td className="text-xs text-gray-600">
                    {e.source === 'manual' ? `수동 · ${e.recorded_by ?? '간호사'}` : '카메라 자동'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-gray-400">
            서버를 켠 뒤의 기록입니다 (임시 저장소).
            {scale !== 1 && ` 시간은 시연 가속 ×${scale} 반영.`}
          </p>
        </section>

        <section className="space-y-3 rounded-xl bg-white p-4 shadow-sm">
          <h3 className="font-bold">압박 부위 (오늘 누적 유지 시간)</h3>
          <Suspense fallback={<div className="h-80 rounded-lg bg-slate-50" />}>
            <Heatmap3D intensities={intensities} current={bed?.posture ?? 'unknown'} />
          </Suspense>
          <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-900">
            ⚠ 실제 압력 측정값이 아닙니다. 자세별 유지 시간으로 눌리는 부위를 추정해 표시합니다.
            드래그해서 돌려 볼 수 있고, 깜빡이는 점은 지금 자세에서 눌리는 부위입니다.
          </p>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            {ranked.slice(0, 8).map((r) => (
              <li key={r.key} className="flex items-center gap-2">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ background: heatColor(r.value) }}
                />
                <span className="flex-1">{r.label}</span>
                <span className="tabular-nums text-xs text-gray-500">
                  {formatElapsed(Math.floor(r.minutes))}
                </span>
              </li>
            ))}
            {ranked.length === 0 && <li className="text-gray-500">아직 기록이 없습니다.</li>}
          </ul>
        </section>
      </div>
    </div>
  )
}
