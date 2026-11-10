import type { Posture } from './posture'

/**
 * 자세별로 눌리는 부위 (PLAN 4장 F4). 키는 3D 모델 메시 이름과 같게 둔다 (CONVENTIONS 5장).
 * ⚠ 실제 압력 측정값이 아니라 "자세별 유지 시간"으로 추정한 값이다 (D-003).
 */
export type Region = {
  key: string
  label: string
  postures: Posture[]
  position: [number, number, number] // 3D 모형 좌표 (환자 왼쪽 = +x, 머리 = -z)
}

export const PRESSURE_REGIONS: Region[] = [
  { key: 'occiput', label: '후두부', postures: ['supine'], position: [0, 0.02, -0.9] },
  { key: 'scapula_left', label: '왼쪽 견갑골', postures: ['supine'], position: [0.1, 0.02, -0.55] },
  {
    key: 'scapula_right',
    label: '오른쪽 견갑골',
    postures: ['supine'],
    position: [-0.1, 0.02, -0.55],
  },
  {
    key: 'sacrum',
    label: '천골·미골(엉치)',
    postures: ['supine', 'sitting'],
    position: [0, 0.02, -0.02],
  },
  { key: 'ischium', label: '좌골(엉덩이 아래)', postures: ['sitting'], position: [0, 0.03, 0.1] },
  { key: 'heel_left', label: '왼쪽 발뒤꿈치', postures: ['supine'], position: [0.1, 0.04, 0.9] },
  {
    key: 'heel_right',
    label: '오른쪽 발뒤꿈치',
    postures: ['supine'],
    position: [-0.1, 0.04, 0.9],
  },
  { key: 'sole_left', label: '왼쪽 발바닥', postures: ['sitting'], position: [0.1, 0.1, 0.98] },
  { key: 'sole_right', label: '오른쪽 발바닥', postures: ['sitting'], position: [-0.1, 0.1, 0.98] },
  { key: 'ear_left', label: '왼쪽 귀', postures: ['left_lateral'], position: [0.13, 0.12, -0.86] },
  {
    key: 'ear_right',
    label: '오른쪽 귀',
    postures: ['right_lateral'],
    position: [-0.13, 0.12, -0.86],
  },
  {
    key: 'shoulder_left',
    label: '왼쪽 어깨',
    postures: ['left_lateral'],
    position: [0.2, 0.12, -0.58],
  },
  {
    key: 'shoulder_right',
    label: '오른쪽 어깨',
    postures: ['right_lateral'],
    position: [-0.2, 0.12, -0.58],
  },
  {
    key: 'trochanter_left',
    label: '왼쪽 대전자(골반 옆)',
    postures: ['left_lateral'],
    position: [0.18, 0.12, 0.0],
  },
  {
    key: 'trochanter_right',
    label: '오른쪽 대전자(골반 옆)',
    postures: ['right_lateral'],
    position: [-0.18, 0.12, 0.0],
  },
  {
    key: 'knee_left',
    label: '왼쪽 무릎 바깥',
    postures: ['left_lateral'],
    position: [0.17, 0.1, 0.42],
  },
  {
    key: 'knee_right',
    label: '오른쪽 무릎 바깥',
    postures: ['right_lateral'],
    position: [-0.17, 0.1, 0.42],
  },
  {
    key: 'ankle_left',
    label: '왼쪽 복사뼈',
    postures: ['left_lateral'],
    position: [0.16, 0.08, 0.82],
  },
  {
    key: 'ankle_right',
    label: '오른쪽 복사뼈',
    postures: ['right_lateral'],
    position: [-0.16, 0.08, 0.82],
  },
]

/**
 * 부위별 강도 0~1. 오늘 그 부위가 눌린 누적 시간 ÷ (체위변경 기준 시간 × 2).
 * 기준 시간 한 번 꽉 채우면 0.5(주황), 두 번이면 1(빨강).
 */
export function regionIntensities(
  totals: Partial<Record<Posture, number>>,
  intervalMin: number,
): Record<string, number> {
  const out: Record<string, number> = {}
  const scale = Math.max(intervalMin, 1) * 2
  for (const r of PRESSURE_REGIONS) {
    const minutes = r.postures.reduce((sum, p) => sum + (totals[p] ?? 0), 0)
    out[r.key] = Math.min(1, minutes / scale)
  }
  return out
}

/** 히트맵 색 계산은 이 함수 하나로 (CONVENTIONS 5장): 0 회색 → 0.5 주황 → 1 빨강 */
export function heatColor(intensity: number): string {
  const t = Math.max(0, Math.min(1, intensity))
  const stops: [number, [number, number, number]][] = [
    [0, [209, 213, 219]],
    [0.5, [245, 158, 11]],
    [1, [220, 38, 38]],
  ]
  const i = t <= 0.5 ? 0 : 1
  const [t0, c0] = stops[i]
  const [t1, c1] = stops[i + 1]
  const k = (t - t0) / (t1 - t0)
  const rgb = c0.map((v, j) => Math.round(v + (c1[j] - v) * k))
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`
}

/** 부위별 오늘 누적 압박 시간 (분, 시연 가속 반영) */
export function regionMinutes(totals: Partial<Record<Posture, number>>): Record<string, number> {
  const out: Record<string, number> = {}
  for (const r of PRESSURE_REGIONS)
    out[r.key] = r.postures.reduce((sum, p) => sum + (totals[p] ?? 0), 0)
  return out
}
