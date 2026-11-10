import { useState } from 'react'
import { ApiError } from '../../shared/api/client'
import { recordManualPosture } from '../../shared/api/devBeds'
import { POSTURE_LABEL, type Posture } from '../../shared/constants/posture'
import { getNurseName } from '../../shared/nurse'
import { useLiveData } from './useLiveBeds'

const CHOICES: Posture[] = ['left_lateral', 'right_lateral', 'supine', 'sitting']

/**
 * 수동 기록·보정. 평소에는 카메라가 자세 변경을 자동으로 기록하므로 작게 둔다.
 * 체위변경이 필요하거나(warning/critical) 인식이 안 될 때(needsCheck)만 크게 보여준다.
 */
export function RepositionButton({ bedCode, prominent }: { bedCode: string; prominent: boolean }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { refresh } = useLiveData()

  const choose = async (posture: Posture) => {
    setBusy(true)
    setError(null)
    try {
      await recordManualPosture(bedCode, posture, getNurseName())
      setOpen(false)
      refresh()
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : '기록하지 못했습니다.')
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return prominent ? (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-3 w-full rounded-lg bg-white/80 px-3 py-2 text-sm font-semibold text-gray-800 shadow-sm ring-1 ring-black/10 hover:bg-white"
      >
        체위변경 완료 기록
      </button>
    ) : (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-3 text-xs text-gray-500 underline underline-offset-2 hover:text-gray-800"
      >
        수동 기록·보정
      </button>
    )
  }

  return (
    <div className="mt-3 space-y-2 rounded-lg bg-white/90 p-2 text-gray-800 ring-1 ring-black/10">
      <p className="text-xs font-semibold">바꾼 자세를 고르세요</p>
      <div className="grid grid-cols-2 gap-1.5">
        {CHOICES.map((p) => (
          <button
            key={p}
            type="button"
            disabled={busy}
            onClick={() => void choose(p)}
            className="rounded-md bg-teal-600 px-2 py-1.5 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
          >
            {POSTURE_LABEL[p]}
          </button>
        ))}
      </div>
      <button type="button" onClick={() => setOpen(false)} className="w-full text-xs text-gray-500">
        취소
      </button>
      {error && <p className="text-xs text-red-700">{error}</p>}
    </div>
  )
}
