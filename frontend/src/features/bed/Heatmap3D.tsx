import { OrbitControls } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import type { Mesh } from 'three'
import type { Posture } from '../../shared/constants/posture'
import { heatColor, PRESSURE_REGIONS } from '../../shared/constants/pressure'

type Props = { intensities: Record<string, number>; current: Posture }

const SKIN = { color: '#e7d3c3', transparent: true, opacity: 0.45 }

/** 단순화한 인체 모형 (바로 누운 모습, 머리 = -z). 메시 대신 기본 도형으로 만든다. */
function Body() {
  const limb = (x: number, z: number, len: number, r: number, key: string) => (
    <mesh key={key} position={[x, 0.12, z]} rotation={[Math.PI / 2, 0, 0]}>
      <capsuleGeometry args={[r, len, 8, 16]} />
      <meshStandardMaterial {...SKIN} />
    </mesh>
  )
  return (
    <group>
      <mesh position={[0, 0.12, -0.85]}>
        <sphereGeometry args={[0.12, 24, 24]} />
        <meshStandardMaterial {...SKIN} />
      </mesh>
      {limb(0, -0.4, 0.4, 0.17, 'torso')}
      {limb(0, -0.02, 0.12, 0.16, 'pelvis')}
      {limb(0.27, -0.33, 0.5, 0.05, 'arm-l')}
      {limb(-0.27, -0.33, 0.5, 0.05, 'arm-r')}
      {limb(0.1, 0.48, 0.72, 0.07, 'leg-l')}
      {limb(-0.1, 0.48, 0.72, 0.07, 'leg-r')}
      {/* 침대 */}
      <mesh position={[0, -0.03, 0]}>
        <boxGeometry args={[0.9, 0.04, 2.2]} />
        <meshStandardMaterial color="#cbd5e1" />
      </mesh>
    </group>
  )
}

function Spot({
  position,
  intensity,
  active,
}: {
  position: [number, number, number]
  intensity: number
  active: boolean
}) {
  const ref = useRef<Mesh>(null)
  useFrame(({ clock }) => {
    if (!ref.current) return
    // 지금 자세로 눌리고 있는 부위는 천천히 커졌다 작아진다
    const s = active ? 1 + 0.25 * Math.sin(clock.elapsedTime * 3) : 1
    ref.current.scale.setScalar(s)
  })
  const color = heatColor(intensity)
  return (
    <mesh ref={ref} position={position}>
      <sphereGeometry args={[0.035 + 0.035 * intensity, 20, 20]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.35 + intensity * 0.6}
      />
    </mesh>
  )
}

export default function Heatmap3D({ intensities, current }: Props) {
  return (
    <Canvas
      camera={{ position: [0.9, 1.25, 1.35], fov: 38 }}
      className="!h-80 rounded-lg bg-slate-50"
    >
      <ambientLight intensity={0.8} />
      <directionalLight position={[2, 3, 1]} intensity={0.9} />
      <Body />
      {PRESSURE_REGIONS.map((r) => (
        <Spot
          key={r.key}
          position={r.position}
          intensity={intensities[r.key] ?? 0}
          active={r.postures.includes(current)}
        />
      ))}
      <OrbitControls enablePan={false} minDistance={1.2} maxDistance={4} />
    </Canvas>
  )
}
