import { NavLink, Outlet } from 'react-router-dom'
import { useLiveData } from '../features/dashboard/useLiveBeds'
import { useAlarm } from '../shared/hooks/useAlarm'
import { useNow } from '../shared/hooks/useNow'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm ${isActive ? 'bg-white/20 font-semibold' : 'hover:bg-white/10'}`

export function Layout() {
  const now = useNow(1000)
  const { alerts } = useLiveData()
  const open = alerts.filter((a) => !a.resolved_at)
  // 확인하지 않은 "체위변경 필요" 알림이 있으면 경고음 (D-012 1단계: 확인할 때까지 반복)
  const alarm = useAlarm(open.some((a) => a.level === 'critical' && !a.acknowledged_at))

  const clock = new Date(now).toLocaleTimeString('ko-KR', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900">
      <header className="sticky top-0 z-10 bg-teal-700 text-white shadow">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-2.5">
          <div className="flex items-baseline gap-3">
            <h1 className="text-lg font-bold">PressCare</h1>
            <span className="text-sm opacity-90">3병동 간호스테이션</span>
            <span className="font-mono text-sm tabular-nums opacity-90">{clock}</span>
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={linkClass}>
              대시보드
            </NavLink>
            <NavLink to="/alerts" className={linkClass}>
              알림
              {open.length > 0 && (
                <span className="ml-1 rounded-full bg-red-500 px-1.5 text-xs font-bold">
                  {open.length}
                </span>
              )}
            </NavLink>
            <NavLink to="/login" className={linkClass}>
              로그인
            </NavLink>
            <button
              type="button"
              onClick={alarm.enabled ? alarm.disable : alarm.enable}
              className={`ml-2 rounded-lg px-3 py-1.5 text-sm font-semibold ${
                alarm.enabled
                  ? 'bg-white/15 text-white'
                  : 'animate-pulse bg-yellow-300 text-gray-900'
              }`}
            >
              {alarm.enabled ? '알림 소리 켜짐' : '알림 소리 켜기'}
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
