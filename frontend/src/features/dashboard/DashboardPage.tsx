import { useState } from 'react'
import { useNow } from '../../shared/hooks/useNow'
import { BedCard } from './BedCard'
import { ConnectionStatus } from './ConnectionStatus'
import { makeDemoBeds } from './demoBeds'

export function DashboardPage() {
  const now = useNow(1000)
  // 예시 데이터는 처음 연 시각 기준으로 한 번만 만든다 (그 뒤로 경과 시간만 흐름)
  const [beds] = useState(() => makeDemoBeds(Date.now()))

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">병동 대시보드</h2>
        <ConnectionStatus />
      </div>
      <p className="rounded-lg border border-dashed border-gray-400 bg-white px-4 py-2 text-sm text-gray-600">
        예시 데이터입니다. Supabase가 연결되면 실제 병상 상태로 바뀝니다.
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {beds.map((bed) => (
          <BedCard key={bed.bedId} bed={bed} now={now} />
        ))}
      </div>
    </section>
  )
}
