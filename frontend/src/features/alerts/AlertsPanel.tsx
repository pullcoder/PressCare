import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../../shared/api/client'
import { ackAlert, type DevAlert } from '../../shared/api/devBeds'
import { getNurseName, setNurseName } from '../../shared/nurse'
import { formatKstTime } from '../../shared/time'
import { useLiveData } from '../dashboard/useLiveBeds'

const LEVEL_TEXT: Record<string, string> = {
  critical: '체위변경 필요',
  warning: '체위변경 곧 필요',
}

function AlertRow({ alert, onAck }: { alert: DevAlert; onAck: (id: number) => void }) {
  const open = !alert.resolved_at
  const critical = alert.level === 'critical'
  return (
    <li
      className={`rounded-lg border px-3 py-2 text-sm ${
        !open
          ? 'border-gray-200 bg-gray-50 text-gray-500'
          : critical
            ? 'border-red-300 bg-red-50 text-red-900'
            : 'border-yellow-300 bg-yellow-50 text-yellow-900'
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <Link
          to={`/beds/${encodeURIComponent(alert.bed_code)}`}
          className="font-semibold hover:underline"
        >
          {alert.bed_code} {alert.patient_name ?? ''}
        </Link>
        <span className="text-xs tabular-nums">{formatKstTime(alert.created_at)}</span>
      </div>
      <p className="mt-0.5">{LEVEL_TEXT[alert.level] ?? alert.level}</p>
      <div className="mt-1 flex items-center justify-between gap-2 text-xs">
        {alert.acknowledged_at ? (
          <span>
            확인 · {alert.acknowledged_by} {formatKstTime(alert.acknowledged_at)}
          </span>
        ) : open ? (
          <button
            type="button"
            onClick={() => onAck(alert.id)}
            className="rounded-md bg-gray-900 px-2.5 py-1 font-semibold text-white hover:bg-gray-700"
          >
            확인
          </button>
        ) : (
          <span>확인 없이 해제</span>
        )}
        {alert.resolved_at && <span>체위변경으로 해제 {formatKstTime(alert.resolved_at)}</span>}
      </div>
    </li>
  )
}

/** 알림 목록·확인 (T3-6). 확인자는 로그인(T4) 전까지 이름을 직접 적는다. */
export function AlertsPanel({ limit, title = '알림' }: { limit?: number; title?: string }) {
  const { alerts, refresh, source } = useLiveData()
  const [name, setName] = useState(getNurseName)
  const [error, setError] = useState<string | null>(null)

  const onAck = async (id: number) => {
    setError(null)
    try {
      await ackAlert(id, name)
      refresh()
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : '확인하지 못했습니다.')
    }
  }

  const open = alerts.filter((a) => !a.resolved_at)
  const done = alerts.filter((a) => a.resolved_at)
  const shown = [...open, ...done].slice(0, limit ?? alerts.length)

  return (
    <section className="space-y-3 rounded-xl bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="font-bold">
          {title}
          {open.length > 0 && (
            <span className="ml-2 rounded-full bg-red-600 px-2 py-0.5 text-xs text-white">
              {open.length}
            </span>
          )}
        </h2>
        <label className="flex items-center gap-1 text-xs text-gray-600">
          확인자
          <input
            value={name}
            onChange={(e) => {
              setName(e.target.value)
              setNurseName(e.target.value)
            }}
            className="w-20 rounded border border-gray-300 px-1.5 py-0.5 text-xs"
          />
        </label>
      </div>
      {source !== 'live' && (
        <p className="text-sm text-gray-500">백엔드가 켜지면 알림이 표시됩니다.</p>
      )}
      {source === 'live' && shown.length === 0 && (
        <p className="text-sm text-gray-500">알림이 없습니다.</p>
      )}
      <ul className="space-y-2">
        {shown.map((a) => (
          <AlertRow key={a.id} alert={a} onAck={(id) => void onAck(id)} />
        ))}
      </ul>
      {error && <p className="text-xs text-red-700">{error}</p>}
    </section>
  )
}
