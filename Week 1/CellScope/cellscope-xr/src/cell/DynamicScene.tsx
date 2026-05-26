import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Object3D, InstancedMesh } from 'three'
import type { SimulationSchema } from '../ai/simulation'
import { clampSimulation } from '../ai/simulation'
import { createSimulationState, stepSimulation } from './SimulationEngine.ts'

export function DynamicScene({ simulation }: { simulation: SimulationSchema }) {
  const sim = useMemo(() => clampSimulation(simulation), [simulation])
  const state = useMemo(() => createSimulationState(sim), [sim])

  const meshRefs = useRef<InstancedMesh[]>([])
  const temp = useMemo(() => new Object3D(), [])

  useFrame((_, delta) => {
    stepSimulation(state, delta)

    state.entities.forEach((entity, idx) => {
      const mesh = meshRefs.current[idx]
      if (!mesh) return

      for (let i = 0; i < entity.count; i++) {
        const p = entity.positions[i]
        temp.position.set(p.x, p.y, p.z)
        temp.scale.setScalar(entity.radius)
        temp.updateMatrix()
        mesh.setMatrixAt(i, temp.matrix)
      }

      mesh.instanceMatrix.needsUpdate = true
    })
  })

  return (
    <group>
      {state.entities.map((entity, i) => (
        <instancedMesh
          key={entity.id}
          ref={(r) => {
            if (r) meshRefs.current[i] = r
          }}
          args={[undefined, undefined, entity.count]}
        >
          {entity.geometry === 'sphere' && <sphereGeometry args={[1, 16, 16]} />}
          {entity.geometry === 'capsule' && <capsuleGeometry args={[0.6, 1.2, 8, 16]} />}
          {entity.geometry === 'box' && <boxGeometry args={[1, 1, 1]} />}
          <meshStandardMaterial color={entity.color} />
        </instancedMesh>
      ))}
    </group>
  )
}