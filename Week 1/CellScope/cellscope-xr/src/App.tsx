import { useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { XR, createXRStore } from '@react-three/xr'
import { DynamicScene } from './cell/DynamicScene'
import { SimulationInput } from './ui/SimulationInput'
import type { SimulationSchema } from './ai/simulation'

const xrStore = createXRStore()

export default function App() {
  const [simulation, setSimulation] = useState<SimulationSchema | null>(null)
  const [status, setStatus] = useState('Provide a paper abstract or results.')
  const apiKeyLoaded = Boolean(import.meta.env.VITE_GEMINI_API_KEY)

  return (
    <div className="w-screen h-screen relative bg-black">
      <button
        onClick={() => xrStore.enterAR()}
        className="absolute top-4 right-4 z-10 bg-blue-600 text-white px-4 py-2 rounded-xl"
      >
        Enter AR
      </button>

      <Canvas>
        <XR store={xrStore}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[2, 4, 2]} intensity={0.8} />
          {simulation ? <DynamicScene simulation={simulation} /> : null}
        </XR>
      </Canvas>

      <SimulationInput
        onSimulation={(sim) => {
          setSimulation(sim)
          setStatus(`${sim.title}: ${sim.description}`)
        }}
        onStatus={(text) => setStatus(text)}
      />

      <div className="absolute bottom-24 left-4 right-4 text-white text-sm bg-black/60 rounded-xl p-3 backdrop-blur-sm">
        <div>{status}</div>
        <div className="mt-1 text-[10px] text-gray-300">
          API key: {apiKeyLoaded ? 'loaded' : 'missing'}
        </div>
      </div>
    </div>
  )
}
