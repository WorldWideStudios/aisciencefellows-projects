export type GeometryType = 'sphere' | 'capsule' | 'box'
export type BehaviorType = 'attract' | 'repel' | 'random_walk' | 'spiral' | 'flocking'

export interface SimulationEntity {
  id: string
  name: string
  color: string
  geometry: GeometryType
  count: number
  radius: number
}

export interface SimulationRule {
  sourceEntityId: string
  targetEntityId: string
  behavior: BehaviorType
  strength: number
}

export interface SimulationSchema {
  title: string
  description: string
  entities: SimulationEntity[]
  rules: SimulationRule[]
}

export function clampSimulation(input: SimulationSchema): SimulationSchema {
  const maxTotal = 200
  let total = 0

  const entities = input.entities.map((e) => {
    const count = Math.max(1, Math.min(200, Math.floor(e.count || 1)))
    total += count
    return {
      ...e,
      count,
      radius: e.radius || 0.08,
      color: e.color || '#66ccff',
    }
  })

  if (total > maxTotal) {
    const scale = maxTotal / total
    const scaled = entities.map((e) => ({
      ...e,
      count: Math.max(1, Math.floor(e.count * scale)),
    }))
    return { ...input, entities: scaled }
  }

  const rules = input.rules.map((r) => ({
    ...r,
    strength: Math.max(0, Math.min(1, r.strength ?? 0.5)),
  }))

  return { ...input, entities, rules }
}