import { useEffect, useState } from 'react'
import { ApiError } from '../../shared/api/client'
import { getHealth, type HealthResponse } from '../../shared/api/health'
import { isSupabaseConfigured } from '../../shared/supabase'

type State =
  { kind: 'loading' } | { kind: 'ok'; health: HealthResponse } | { kind: 'error'; message: string }

const SUPABASE_TEXT: Record<HealthResponse['supabase'], string> = {
  connected: '연결됨',
  not_configured: '설정 전',
  unreachable: '연결 안 됨',
}

/** 개발용: backend 와 Supabase 설정 상태를 보여준다. */
export function ConnectionStatus() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    let alive = true
    getHealth()
      .then((health) => alive && setState({ kind: 'ok', health }))
      .catch((err: unknown) => {
        const message = err instanceof ApiError ? err.message : '알 수 없는 오류'
        if (alive) setState({ kind: 'error', message })
      })
    return () => {
      alive = false
    }
  }, [])

  const backend =
    state.kind === 'loading'
      ? '확인 중…'
      : state.kind === 'ok'
        ? '연결됨'
        : `연결 안 됨 (${state.message})`
  const supabase =
    state.kind === 'ok'
      ? SUPABASE_TEXT[state.health.supabase]
      : isSupabaseConfigured()
        ? '설정됨'
        : '설정 전'

  return (
    <dl className="flex flex-wrap gap-x-6 gap-y-1 rounded-lg bg-white px-4 py-2 text-sm text-gray-700 shadow-sm">
      <div className="flex gap-2">
        <dt className="font-semibold">백엔드</dt>
        <dd>{backend}</dd>
      </div>
      <div className="flex gap-2">
        <dt className="font-semibold">Supabase</dt>
        <dd>{supabase}</dd>
      </div>
    </dl>
  )
}
