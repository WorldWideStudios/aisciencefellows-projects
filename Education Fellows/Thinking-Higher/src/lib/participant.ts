// --- Participant Metadata ---
// Collects browser/device metadata for research-grade profiling.
// Patterns from NivTurk (nivlab.github.io/nivturk):
//   - Browser & OS fingerprint for controlling device effects on RT
//   - Screen dimensions for controlling UI layout effects
//   - Prolific/platform ID passthrough for linking to external data
//
// For Prolific integration via Deliberate Lab:
//   - Prolific passes PROLIFIC_PID, STUDY_ID, SESSION_ID as URL params
//   - Completion redirects use Prolific's completion URL with the participant code
//   - We store the Prolific PID as participantId for cross-platform data joining

export interface ParticipantMetadata {
  // Platform IDs (Prolific, MTurk, or anonymous)
  participantId: string;
  prolificPid: string | null;
  studyId: string | null;
  sessionCode: string | null;

  // Device fingerprint (affects RT interpretation)
  userAgent: string;
  platform: string;
  language: string;
  screenWidth: number;
  screenHeight: number;
  devicePixelRatio: number;
  touchCapable: boolean;

  // Timing context
  timezone: string;
  collectedAt: number;
}

// Collect metadata from the browser environment.
// Called once at simulation start.
export function collectParticipantMetadata(): ParticipantMetadata {
  // Extract Prolific URL params if present
  const params = new URLSearchParams(window.location.search);

  return {
    participantId:
      params.get("PROLIFIC_PID") ||
      params.get("participant_id") ||
      params.get("workerId") ||
      `anon-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    prolificPid: params.get("PROLIFIC_PID"),
    studyId: params.get("STUDY_ID"),
    sessionCode: params.get("SESSION_ID"),

    userAgent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    screenWidth: window.screen.width,
    screenHeight: window.screen.height,
    devicePixelRatio: window.devicePixelRatio || 1,
    touchCapable: "ontouchstart" in window || navigator.maxTouchPoints > 0,

    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    collectedAt: Date.now(),
  };
}

// NivTurk MTurk patterns worth noting for Prolific integration:
//
// 1. COMPLETION REDIRECT: After simulation completes, redirect to Prolific's
//    completion URL. Pattern:
//      window.location.href = `https://app.prolific.com/submissions/complete?cc=${COMPLETION_CODE}`;
//    The completion code is set per-study in Prolific dashboard.
//
// 2. DUPLICATE PREVENTION: NivTurk uses cookies to prevent re-participation.
//    With Prolific, this is handled by Prolific's platform — participants can't
//    re-enter a completed study. But we should still check participantId against
//    completed sessions in our DB.
//
// 3. ONLINE REJECTION: NivTurk allows mid-experiment rejection (e.g., failing
//    attention checks). With Prolific, you approve/reject via their API after
//    data review. We should flag low-quality sessions for manual review.
//
// 4. METADATA FOR RT NORMALIZATION: NivTurk stores OS, browser, and IP.
//    Critical for RT research — mobile participants have 50-100ms longer RTs
//    than desktop. We should flag mobile/touch devices and potentially exclude
//    or normalize their RT data.
