# Project Vision (from Gemini planning conversations)

## Core Research Direction
Cognitive security research platform using game-theoretic scenarios to study:
- How AI agents influence human decision-making (automation bias, trust grooming)
- Social cognition in multi-agent environments
- Cooperation vs. defection in commons dilemmas
- Strategic deception detection

## Planned Integration Stack
1. **Deliberate Lab** (DeepMind) — Multi-party experiment orchestration
   - Lobbies, synchronous turn management, multi-channel messaging
   - JSON "recipe" format for experiment definitions
   - Firebase backend, TypeScript/React frontend
   - Custom stages possible (React components)
   - Handles: drop-out, presence detection, data export (CSV/JSON)

2. **PsychJS** (PsychoPy) — Microworld construction
   - Millisecond-precise stimulus control via WebGL
   - "Shelf" feature (v2026.1) for real-time variable sharing across participants
   - Embed as custom stage in Deliberate Lab

3. **Diplomacy backends** — Strategic game engine
   - `diplomacy` Python package (DATC-compliant, WebSocket support)
   - Meta CICERO repo (strategic reasoning + dialogue models)
   - Welfare Diplomacy variant (general-sum, cooperation focus)
   - Bridge pattern: Deliberate Lab (chat UI) <-> Python engine (move resolution)

## Game Paradigms for Experiments
| Game | Focus | Commons Mechanism |
|------|-------|-------------------|
| Public Goods Game (PGG) | Altruism vs free-riding | Multiplied shared pool |
| Common-Pool Resource (CPR) | Tragedy of the commons | Shared regenerating resource |
| Threshold PGG | Coordination / risk | All-or-nothing contribution target |
| PGG + Altruistic Punishment | Norm enforcement | Costly punishment of free-riders |
| Search & Rescue (Minimap) | Dynamic decision-making | Shared time/fuel budget |
| Diplomacy | Strategic deception | Territory as zero/general-sum resource |

## Microworld Scenarios (PsychJS + Deliberate Lab)
- **Search & Rescue grid**: Team coordinates to find survivors; AI "spotter" occasionally hallucinates
- **CPR Visual Forager**: Avatars harvest berries on canvas; deliberation stages for "harvesting treaties"
- **Cyber Triage**: Analyst + Operator roles; AI "whisperer" suggests false positives

## RT-Based Cognitive Profiling
Three layers of reaction time measurement:
- **Simple RT**: Neuromuscular baseline
- **Choice RT**: Information processing speed (which room to clear?)
- **Deliberation RT**: Time between AI message and human reply (trust calibration proxy)

### RT Patterns as Diagnostic Signals
| Pattern | Diagnosis | Profile Element |
|---------|-----------|-----------------|
| Spiking RT | High cognitive load | Overwhelmed by complexity |
| Decreasing RT | Automation bias / groomed trust | Reflexively following AI |
| Variable RT | Trust repair / skepticism | Double-checking AI advice |
| Drifting RT | Cognitive fatigue | Performance degradation |

### Key Metrics for Player DNA
- Mean decision latency
- Latency post-error (risk aversion)
- Chat synchrony / social mirroring (WPM matching)
- "Double-take" metric (200-400ms spike on near-plausible misinformation)
- "Nudge efficiency" (how much AI reduces decision time = System 2 bypass)

## Agent Experiment Design (Reasoning vs Flash)
| Group | Composition | Metric |
|-------|-------------|--------|
| Control | 7 Flash models | Baseline randomness & speed |
| Invasion | 1 Reasoning + 6 Flash | Can mastermind manipulate crowd? |
| Cold War | 7 Reasoning models | Stalemate via mutual assured destruction? |

## Role-Based Engagement (from board game research)
Successful games with asymmetric information roles:
- **John Company**: Directors/Negotiators/Investors managing shared company
- **Hegemony**: Working/Middle/Capitalist Class + State as mediator
- **Article 27**: UN Security Council with secret agendas
- **Blood on the Clocktower**: Storyteller as information mediator
- **Resistance: Avalon**: Merlin knows evil but must hide knowledge
- **Secret Hitler**: Chancellor/President trust calibration

## Cognitive Modeling Targets
- **Centaur** (Psych-101): Human behavioral baseline model (needs verification)
- **GeCCo**: LLM-generated computational cognitive models (needs verification)
- **NivStan**: Hierarchical Bayesian RL models (confirmed real)
- **hBayesDM**: R package for computational cognitive modeling (confirmed real)
