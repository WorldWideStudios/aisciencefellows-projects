import { useState } from 'react'
import { generateSimulationFromText } from '../ai/gemini'
import type { SimulationSchema } from '../ai/simulation'
import { clampSimulation } from '../ai/simulation'

interface Props {
  onSimulation: (sim: SimulationSchema) => void
  onStatus: (text: string) => void
}

const demo: SimulationSchema = {
  title: 'Chemotaxis Demo',
  description: 'Simple attract + random walk mix',
  entities: [
    { id: 'A', name: 'Motile', color: '#66ccff', geometry: 'sphere', count: 120, radius: 0.06 },
    { id: 'B', name: 'Signal', color: '#ffaa33', geometry: 'sphere', count: 8, radius: 0.12 },
  ],
  rules: [
    { sourceEntityId: 'A', targetEntityId: 'B', behavior: 'attract', strength: 0.8 },
    { sourceEntityId: 'A', targetEntityId: 'A', behavior: 'random_walk', strength: 0.4 },
  ],
}

export function SimulationInput({ onSimulation, onStatus }: Props) {
  const [text, setText] = useState('')

  const handleGenerate = async () => {
    if (!text.trim()) return
    try {
      onStatus('Generating simulation from paper text...')
      const sim = await generateSimulationFromText(text)
      onSimulation(clampSimulation(sim))
    } catch (e: any) {
      onStatus(`Failed: ${e.message}`)
    }
  }

  return (
    <div className="absolute bottom-4 left-4 right-4 flex gap-2">
      <textarea
        className="flex-1 bg-black/60 text-white rounded-xl px-4 py-2 text-xs backdrop-blur-sm outline-none h-16"
        placeholder="Paste abstract or results..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="flex flex-col gap-2">
        <button
          onClick={handleGenerate}
          className="bg-blue-600 text-white px-4 py-2 rounded-xl text-xs"
        >
          Generate
        </button>
        <button
          onClick={() => onSimulation(clampSimulation(demo))}
          className="bg-gray-700 text-white px-4 py-2 rounded-xl text-xs"
        >
          Demo
        </button>
      </div>
    </div>
  )
}