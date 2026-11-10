import { useMemo, useState, type ReactNode } from 'react'
import { useNow } from '../../shared/hooks/useNow'
import { getPref, setPref } from '../../shared/nurse'
import { AlertsPanel } from '../alerts/AlertsPanel'
import { BedCard } from './BedCard'
import { makeDemoBeds } from './demoBeds'
import { toBedView, useLiveData } from './useLiveBeds'
import { groupByRoom, sortBeds, summarize, type SortMode } from './ward'

function Chip({ children, tone }: { children: ReactNode; tone: string }) {
  return <span className={`rounded-full px-3 py-1 text-sm font-semibold ${tone}`}>{children}</span>
}

export function DashboardPage() {
  const now = useNow(1000)
  const live = useLiveData()
  const [demoBeds] = useState(() => makeDemoBeds(Date.now()))
  const [mode, setMode] = useState<SortMode>(() =>
    getPref('sort', 'urgent') === 'bed' ? 'bed' : 'urgent',
  )

  const isLive = live.source === 'live' && live.beds !== null
  const beds = useMemo(
    () => (isLive && live.beds ? live.beds.beds.map(toBedView) : demoBeds),
    [isLive, live.beds, demoBeds],
  )
  const intervalMin = live.beds?.reposition_interval_min ?? 120
  const scale = live.beds?.time_scale ?? 1
  const summary = summarize(beds)
  const groups = groupByRoom(sortBeds(beds, mode))

  const changeMode = (m: SortMode) => {
    setMode(m)
    setPref('sort', m)
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Chip tone="bg-white text-gray-800 ring-1 ring-gray-200">전체 {summary.total}</Chip>
            <Chip tone="bg-red-600 text-white">체위변경 필요 {summary.critical}</Chip>
            <Chip tone="bg-yellow-300 text-yellow-950">곧 필요 {summary.warning}</Chip>
            <Chip tone="bg-gray-700 text-white">확인 필요 {summary.check}</Chip>
            <Chip tone="bg-gray-200 text-gray-600">연결 끊김 {summary.offline}</Chip>
          </div>
          <div className="flex rounded-lg bg-white p-0.5 text-sm shadow-sm ring-1 ring-gray-200">
            {(
              [
                ['urgent', '급한 순'],
                ['bed', '병상 순'],
              ] as const
            ).map(([m, label]) => (
              <button
                key={m}
                type="button"
                onClick={() => changeMode(m)}
                className={`rounded-md px-3 py-1 ${mode === m ? 'bg-teal-700 font-semibold text-white' : 'text-gray-600'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {!isLive && (
          <p className="rounded-lg border border-dashed border-gray-400 bg-white px-4 py-2 text-sm text-gray-600">
            예시 데이터입니다. 백엔드가 켜지면 실제 병상 상태로 바뀝니다.
          </p>
        )}
        {isLive && beds.length === 0 && (
          <p className="rounded-lg border border-dashed border-gray-400 bg-white px-4 py-2 text-sm text-gray-600">
            연결된 병상이 없습니다. 엣지 프로그램(python -m edge.main)을 실행하세요.
          </p>
        )}

        {groups.map(([room, list]) => (
          <div key={room} className="space-y-2">
            <h3 className="text-sm font-bold text-gray-600">
              {room} <span className="font-normal">· {list.length}병상</span>
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {list.map((bed) => (
                <BedCard key={bed.bedId} bed={bed} now={now} intervalMin={intervalMin} />
              ))}
            </div>
          </div>
        ))}

        {isLive && (
          <p className="text-xs text-gray-400">
            시연 모드 · 임시 메모리 저장소(Supabase 연결 전)
            {scale !== 1 && ` · 시간 ×${scale} (화면의 1분 = 실제 ${60 / scale}초)`}
          </p>
        )}
      </section>

      <aside className="space-y-4">
        <AlertsPanel limit={8} />
      </aside>
    </div>
  )
}
