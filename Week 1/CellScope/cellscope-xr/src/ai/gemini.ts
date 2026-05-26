import type { SimulationSchema } from './simulation'

const GEMINI_ENDPOINT =
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'

const API_KEY = import.meta.env.VITE_GEMINI_API_KEY || ''

async function callGemini(prompt: string): Promise<string> {
  if (!API_KEY) {
    throw new Error(
      'Missing VITE_GEMINI_API_KEY. Ensure .env is in the cellscope-xr folder and restart the dev server from that folder.'
    )
  }
  const res = await fetch(`${GEMINI_ENDPOINT}?key=${API_KEY}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
  })
  const data = await res.json()
  return data.candidates?.[0]?.content?.parts?.[0]?.text ?? ''
}

function stripJson(raw: string): string {
  return raw.replace(/```json/g, '').replace(/```/g, '').trim()
}

export async function generateSimulationFromText(text: string): Promise<SimulationSchema> {
  const prompt = `You are a scientific simulator architect. Produce a JSON configuration for a physics simulation based on the following text.
The simulation supports these behaviors: 'attract', 'repel', 'random_walk', 'spiral', 'flocking'.
Keep particle counts low (under 200 total) to ensure performance.

Output ONLY valid JSON matching this TypeScript interface, with no markdown code block formatting:
{
  "title": "string",
  "description": "string",
  "entities": [
    { "id": "string", "name": "string", "color": "string (hex)", "geometry": "sphere" | "capsule" | "box", "count": number, "radius": number }
  ],
  "rules": [
    { "sourceEntityId": "string", "targetEntityId": "string", "behavior": "string", "strength": number }
  ]
}

Text to analyze:
${text}`

  const raw = await callGemini(prompt)
  const clean = stripJson(raw)
  return JSON.parse(clean) as SimulationSchema
}