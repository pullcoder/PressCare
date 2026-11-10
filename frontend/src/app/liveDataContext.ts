import { createContext } from 'react'
import type { DevAlert, DevBedsResponse } from '../shared/api/devBeds'

export type LiveData = {
  source: 'loading' | 'live' | 'unavailable' // unavailable: backend 꺼짐 → 예시 데이터
  beds: DevBedsResponse | null
  alerts: DevAlert[]
  refresh: () => void
}

export const LiveDataContext = createContext<LiveData>({
  source: 'loading',
  beds: null,
  alerts: [],
  refresh: () => {},
})
