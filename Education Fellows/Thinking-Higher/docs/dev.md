# ThinkHigher — Dev Notes

## Environment Setup

Copy `.env.example` to `.env.local` and fill in the values below.

```env
# ── LLM ───────────────────────────────────────────────────────────────────────
GEMINI_API_KEY=            # Google AI Studio key — https://aistudio.google.com/app/apikey
GEMINI_MODEL=gemini-2.5-flash   # optional override; defaults to gemini-2.5-flash

# ── Text-to-Speech (Amazon Polly) ─────────────────────────────────────────────
AWS_ACCESS_KEY_ID=         # IAM user key — needs AmazonPollyReadOnlyAccess
AWS_SECRET_ACCESS_KEY=     # IAM user secret
AWS_REGION=us-east-1       # region where Polly is available (us-east-1 recommended)

# ── Speech-to-Text ────────────────────────────────────────────────────────────
# No separate key — STT uses Gemini multimodal transcription via GEMINI_API_KEY above.

# ── Auth (NextAuth v5) ────────────────────────────────────────────────────────
AUTH_SECRET=               # random string — run: openssl rand -base64 32
GOOGLE_CLIENT_ID=          # OAuth 2.0 client ID
GOOGLE_CLIENT_SECRET=      # OAuth 2.0 client secret

# ── Database (Vercel Postgres) ────────────────────────────────────────────────
POSTGRES_URL=              # postgres://... from Vercel dashboard

# ── Email (Resend) ────────────────────────────────────────────────────────────
RESEND_API_KEY=            # re_...
```

### Getting each key

**Gemini (`GEMINI_API_KEY`)**
1. Go to https://aistudio.google.com/app/apikey
2. Create a new key. Enable billing on the associated Google Cloud project to avoid free-tier rate limits.

**Amazon Polly (`AWS_*`)**
1. AWS Console → IAM → Users → Create user
2. Attach policy: `AmazonPollyReadOnlyAccess`
3. Security credentials tab → Create access key → choose "Application running outside AWS"
4. Copy Access key ID and Secret access key

**Speech-to-Text** — no key needed. STT goes through Gemini's multimodal `generateContent` using the same `GEMINI_API_KEY`.

**Auth secret**
```bash
openssl rand -base64 32
```

---

## Running locally

```bash
npm install
npm run dev        # starts on http://localhost:3000
```

> Use `http://localhost:3000` (not your network IP) — the mic requires a secure context and localhost qualifies.

---

## Changelog

### Speech-to-text: Gemini multimodal (replaces Google Cloud STT v1)

- `src/app/api/stt/route.ts` — now sends the recorded audio inline to Gemini (`generateContent`, model from `GEMINI_MODEL`, default `gemini-1.5-flash`) with a verbatim-transcript prompt at `temperature 0.1`. The `GOOGLE_STT_API_KEY` is gone — STT rides on `GEMINI_API_KEY`.
- `src/hooks/useSpeechInput.ts` — removed the `AudioContext` 1.5 s silence auto-stop; recording is now stopped manually by tapping the mic again. Added explicit `MediaRecorder` codec selection (`audio/webm;codecs=opus` → `audio/webm` → browser default) and `getUserMedia` audio constraints (`echoCancellation` / `noiseSuppression` / `autoGainControl`) to avoid the macOS Continuity Camera mic. Added user-visible status text via `interimText`.

### Speech interface (voice-first mode)

Added a full speech layer on top of the existing text chat.

**New API routes**
- `src/app/api/tts/route.ts` — proxies text → Amazon Polly → returns `audio/mpeg`. Accepts `{ text, voiceId }`. Whitelists valid Polly voice IDs; falls back to `"Joanna"`.
- `src/app/api/stt/route.ts` — proxies audio blob → Gemini multimodal transcription (model from `GEMINI_MODEL`, default `gemini-1.5-flash`; verbatim-transcript prompt, `temperature 0.1`) → returns `{ transcript }`. Uses `multipart/form-data`. *(Originally Google Cloud STT v1 — see the entry above.)*

**New hooks**
- `src/hooks/useSpeechOutput.ts` — sentence-chunks the AI reply, fetches Polly audio per chunk, plays sequentially. `speak(text, voiceId?)` accepts an optional per-call voice override to avoid React state timing issues when the stage changes.
- `src/hooks/useSpeechInput.ts` — `MediaRecorder` capture (prefers `audio/webm;codecs=opus`, falls back per browser) with `getUserMedia` echo-cancel / noise-suppress / AGC constraints. Two states: `idle` / `listening`; stop is manual (tap the mic again). `interimText` surfaces status — "Listening…", "Transcribing…", "Could not hear anything.", "Microphone access denied", "Error: could not transcribe". Fires `onTranscript(text)` callback. *(Earlier revisions used `AudioContext` 1.5 s silence auto-stop — removed; see the entry above.)*

**New components**
- `src/components/MicButton.tsx` — icon-only mic button; `idle` shows mic SVG, `listening` shows stop square with dual pulse rings.
- `src/components/VoiceBubble.tsx` — WhatsApp-style voice message tile with deterministic waveform (seeded by duration) and a `0:07`-style duration label.

**New utility**
- `src/lib/speech.ts` — `chunkBySentence`, `fetchTTSAudio`, `fetchSTTTranscript`.

**Schema changes**
- `src/lib/types.ts` — added `pollyVoice?: string` to `AgentProfile` and `AgentDefinition`.
- All three scenario JSONs (`001`, `002`, `003`) have `pollyVoice` set per agent.

**Simulation changes (`Simulation.tsx`, `SimulationV2.tsx`)**
- `inputMode: "voice" | "type"` — default `"voice"`, persisted to `localStorage`.
- Voice mode: centered `MicButton` + keyboard-icon toggle. Type mode: textarea + mic-icon toggle.
- AI messages: wave-bar animation while Polly is speaking; per-message eye-icon button to reveal transcript (disabled while the message is still playing).
- User voice messages render as `VoiceBubble` instead of text bubble.
- `sendMessageRef` pattern used to break circular declaration dependency between `onTranscript` and `sendMessage`.

**Bug fixes**
- Wrong Polly voice on stage opener — fixed by passing `voiceId` directly to `speak()` instead of relying on React state that hasn't updated yet when `loadStage` → `getAIOpener` fires.
- "Show" button revealing all previous messages — replaced global `showAIText: boolean` with per-message `revealedMsgIds: Set<string>`.
- "Show" button clickable during speech — button is disabled and dimmed while `isSpeaking` is true for that message.
- `src/app/api/chat/route.ts` — added 3-attempt exponential backoff retry (1 s, 2 s) on Gemini 503 responses.

### Earlier fixes
- `src/app/globals.css` — fixed `body { overflow: hidden }` that prevented all pages from scrolling.
- `src/app/simulations/page.tsx` — fixed 404 on Vela simulation card (wrong href).
- Git author rewritten to personal account (m9h / morgan.hough@gmail.com) via `git filter-branch`.

---

## Architecture notes

### Voice flow
```
User taps mic → MediaRecorder captures WebM/Opus
  → user taps mic again to stop
  → POST /api/stt  (audio blob, multipart/form-data)
  → Gemini (multimodal transcription)  → transcript string
  → sendMessage(transcript)
  → LLM reply arrives
  → POST /api/tts per sentence  (text + voiceId)
  → Amazon Polly   → audio/mpeg
  → played sequentially via <audio> element
  → isSpeaking = true → wave-bar animates
  → isSpeaking = false → Show button becomes active
```

### Polly voice assignment
Each agent in the scenario JSON declares its own voice:
```json
"agentProfile": {
  "pollyVoice": "Joanna"
}
```
The voice is read at call time (`speak(text, stage.agentProfile.pollyVoice)`) so there is no dependency on React state timing. Fallback is `"Joanna"` if the field is absent.

### Gemini retry
`/api/chat` retries up to 3 times on 503 with 1 s / 2 s backoff. 503 from Gemini means "temporarily overloaded" — it is not a billing or quota error and almost always resolves within a few seconds.
