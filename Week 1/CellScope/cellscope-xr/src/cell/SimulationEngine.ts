import { Vector3 } from 'three'
import type { SimulationSchema } from '../ai/simulation'

type EntityState = {
  id: string
  geometry: 'sphere' | 'capsule' | 'box'
  color: string
  count: number
  radius: number
  positions: Vector3[]
  velocities: Vector3[]
}

type RuleState = {
  sourceEntityId: string
  targetEntityId: string
  behavior: string
  strength: number
}

export type SimulationState = {
  entities: EntityState[]
  rules: RuleState[]
  bounds: number
}

function randInSphere(radius: number) {
  const v = new Vector3(
    (Math.random() * 2 - 1) * radius,
    (Math.random() * 2 - 1) * radius,
    (Math.random() * 2 - 1) * radius
  )
  return v
}

export function createSimulationState(sim: SimulationSchema): SimulationState {
  const bounds = 1.5
  const entities = sim.entities.map((e) => ({
    id: e.id,
    geometry: e.geometry,
    color: e.color,
    count: e.count,
    radius: e.radius,
    positions: Array.from({ length: e.count }, () => randInSphere(bounds * 0.8)),
    velocities: Array.from({ length: e.count }, () => randInSphere(0.02)),
  }))

  return { entities, rules: sim.rules, bounds }
}

function centroid(entity: EntityState): Vector3 {
  const c = new Vector3()
  for (const p of entity.positions) c.add(p)
  return c.divideScalar(entity.count || 1)
}

export function stepSimulation(state: SimulationState, delta: number) {
  const dt = Math.min(delta, 0.033)
  const centroids = new Map<string, Vector3>()
  const avgVels = new Map<string, Vector3>()

  for (const e of state.entities) {
    centroids.set(e.id, centroid(e))
    const v = new Vector3()
    for (const vel of e.velocities) v.add(vel)
    avgVels.set(e.id, v.divideScalar(e.count || 1))
  }

  for (const rule of state.rules) {
    const src = state.entities.find((e) => e.id === rule.sourceEntityId)
    const tgt = state.entities.find((e) => e.id === rule.targetEntityId)
    if (!src || !tgt) continue

    const targetCenter = centroids.get(tgt.id) || new Vector3()
    const targetVel = avgVels.get(src.id) || new Vector3()

    for (let i = 0; i < src.count; i++) {
      const pos = src.positions[i]
      const vel = src.velocities[i]
      const dir = targetCenter.clone().sub(pos).normalize()

      if (rule.behavior === 'random_walk') {
        vel.add(randInSphere(0.02).multiplyScalar(rule.strength))
      }

      if (rule.behavior === 'attract') {
        vel.add(dir.multiplyScalar(0.03 * rule.strength))
      }

      if (rule.behavior === 'repel') {
        vel.add(dir.multiplyScalar(-0.03 * rule.strength))
      }

      if (rule.behavior === 'spiral') {
        const up = new Vector3(0, 1, 0)
        const swirl = dir.clone().cross(up).normalize()
        vel.add(swirl.multiplyScalar(0.025 * rule.strength))
      }

      if (rule.behavior === 'flocking') {
        const align = targetVel.clone().sub(vel)
        vel.add(align.multiplyScalar(0.02 * rule.strength))
      }
    }
  }

  for (const e of state.entities) {
    for (let i = 0; i < e.count; i++) {
      const pos = e.positions[i]
      const vel = e.velocities[i]

      vel.multiplyScalar(0.98)
      vel.clampLength(0, 0.06)

      pos.addScaledVector(vel, dt)

      if (pos.length() > state.bounds) {
        pos.multiplyScalar(0.98)
        vel.multiplyScalar(-0.5)
      }
    }
  }
}
