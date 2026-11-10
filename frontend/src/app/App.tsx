import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AlertsPage } from '../features/alerts/AlertsPage'
import { LoginPage } from '../features/auth/LoginPage'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { Layout } from './Layout'
import { LiveDataProvider } from './LiveDataProvider'

// 3D(Three.js)가 무거워서 병상 상세 화면은 열 때 불러온다
const BedDetailPage = lazy(() => import('../features/bed/BedDetailPage'))

export default function App() {
  return (
    <LiveDataProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route
              path="beds/:code"
              element={
                <Suspense fallback={<p className="text-sm text-gray-500">불러오는 중…</p>}>
                  <BedDetailPage />
                </Suspense>
              }
            />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LiveDataProvider>
  )
}
