import { useContext } from 'react'
import { LiveDataContext, type LiveData } from '../../app/liveDataContext'
import type { DevBed } from '../../shared/api/devBeds'
import type { BedView } from './types'

export function toBedView(b: DevBed): BedView {
  return {
    bedId: b.bed_code,
    code: b.bed_code,
    patientName: b.patient_name,
    posture: b.current_posture,
    postureSince: b.posture_since,
    status: b.status,
    elapsedMin: b.elapsed_min,
    keypoints: b.keypoints,
    needsCheck: b.needs_check,
    live: true,
    simulated: b.simulated,
    alert: b.alert,
  }
}

/** 병상·알림 실시간 데이터 (LiveDataProvider 가 1초마다 읽어 둔 값). */
export function useLiveData(): LiveData {
  return useContext(LiveDataContext)
}
