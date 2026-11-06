import { useState, type ReactNode } from 'react'
import { useNow } from '../../shared/hooks/useNow'
import { BedCard } from './BedCard'
import { ConnectionStatus } from './ConnectionStatus'
import { makeDemoBeds } from './demoBeds'
import { useLiveBeds } from './useLiveBeds'

function Notice({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-dashed border-gray-400 bg-white px-4 py-2 text-sm text-gray-600">
      {children}
    </p>
  )
}

export function DashboardPage() {
  const now = useNow(1000)
  const live = useLiveBeds(1000)
  // 예시 데이터는 처음 연 시각 기준으로 한 번만 만든다 (그 뒤로 경과 시간만 흐름)
  const [demoBeds] = useState(() => makeDemoBeds(Date.now()))

  const isLive = live.source === 'live'
  const beds = isLive ? live.beds : demoBeds

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">병동 대시보드</h2>
        <ConnectionStatus />
      </div>
      {isLive ? (
        <Notice>
          실시간 (임시 메모리 저장소, Supabase 연결 전)
          {live.timeScale !== 1 && (
            <strong className="ml-2 text-teal-700">시연 시간 ×{live.timeScale}</strong>
          )}
        </Notice>
      ) : (
        <Notice>예시 데이터입니다. 백엔드가 켜지면 실제 병상 상태로 바뀝니다.</Notice>
      )}
      {isLive && beds.length === 0 && (
        <Notice>연결된 병상이 없습니다. 엣지 프로그램(python -m edge.main)을 실행하세요.</Notice>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {beds.map((bed) => (
          <BedCard key={bed.bedId} bed={bed} now={now} />
        ))}
      </div>
    </section>
  )
}
