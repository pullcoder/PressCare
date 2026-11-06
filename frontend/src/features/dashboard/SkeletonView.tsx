import type { Keypoints } from './types'

// MediaPipe 관절 번호 (edge/edge/pose/base.py 의 KP 와 같음)
const LINES: [number, number][] = [
  [7, 0],
  [0, 8], // 귀–코–귀
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16], // 어깨·팔
  [11, 23],
  [12, 24],
  [23, 24], // 몸통
  [23, 25],
  [25, 27],
  [24, 26],
  [26, 28], // 다리
]
const MIN_VIS = 0.3

/** 관절 좌표만으로 그린 뼈대. 영상은 서버로 오지 않는다 (D-002). */
export function SkeletonView({ keypoints }: { keypoints: Keypoints }) {
  if (keypoints.length !== 33) return null
  return (
    <svg
      viewBox="0 0 1 1"
      className="h-24 w-24 shrink-0 rounded-md bg-white/70"
      aria-label="관절 위치"
    >
      {LINES.map(([a, b]) => {
        const [ax, ay, av] = keypoints[a]
        const [bx, by, bv] = keypoints[b]
        if (Math.min(av, bv) < MIN_VIS) return null
        return (
          <line
            key={`${a}-${b}`}
            x1={ax}
            y1={ay}
            x2={bx}
            y2={by}
            stroke="currentColor"
            strokeWidth={0.02}
            strokeLinecap="round"
          />
        )
      })}
    </svg>
  )
}
