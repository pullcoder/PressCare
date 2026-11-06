import { NavLink, Outlet } from 'react-router-dom'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm ${isActive ? 'bg-white/20 font-semibold' : 'hover:bg-white/10'}`

export function Layout() {
  return (
    <div className="min-h-screen bg-gray-100 text-gray-900">
      <header className="bg-teal-700 text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <h1 className="text-lg font-bold">PressCare</h1>
          <nav className="flex gap-1">
            <NavLink to="/" end className={linkClass}>
              대시보드
            </NavLink>
            <NavLink to="/login" className={linkClass}>
              로그인
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
