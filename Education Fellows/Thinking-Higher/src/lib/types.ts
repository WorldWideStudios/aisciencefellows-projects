// --- Scenario Schema Types ---

export interface SkillDimension {
  key: string;
  label: string;
  weight: number;
}

export interface AssessmentConfig {
  scoringMethod: string;
  skillDimensions: SkillDimension[];
  evaluatorPrompt: string;
}

export interface TurnConfig {
  minTurns: number;
  maxTurns: number;
  wrapUpSignalTurn: number;
  maxCharsPerMessage?: number;
}

export interface SituationParticipant {
  name: string;
  role: string;
  isYou?: boolean;
  avatarColor?: string;
}

export interface SituationBriefData {
  context: string;
  participants: SituationParticipant[];
  goal: string;
  hints: string[];
}

export interface ComprehensionOption {
  id: string;
  text: string;
  correct: boolean;
}

export interface ComprehensionQuestion {
  id: string;
  type: "mc" | "openended";
  prompt: string;
  options?: ComprehensionOption[];
}

export type StageType = "chat" | "video-chat" | "chat-artifact";

// --- Deliberate Lab-compatible Agent Types ---
// Maps to PAIR-code/deliberate-lab utils/src/agent.ts

export type AgentPersonaType = "participant" | "mediator";
export type ReasoningLevel = "off" | "minimal" | "low" | "medium" | "high";

export interface AgentModelSettings {
  apiType: string;
  modelName: string;
}

export interface ModelGenerationConfig {
  maxTokens?: number;
  temperature?: number;
  topP?: number;
  reasoningLevel?: ReasoningLevel;
  reasoningBudget?: number;
}

export interface AgentChatSettings {
  wordsPerMinute: number | null;
  minMessagesBeforeResponding: number;
  canSelfTriggerCalls: boolean;
  maxResponses: number | null;
  initialMessage: string;
}

export interface AgentDefaultProfile {
  name: string;
  avatar: string;
  pronouns: string | null;
}

export interface AgentProfile {
  // ThinkHigher display fields
  name: string;
  role: string;
  avatar: string;
  color: string;
  personaPrompt: string;
  assessmentRubric: string;
  pollyVoice?: string;
  // Deliberate Lab-compatible fields
  agentPersonaType: AgentPersonaType;
  description: string;
  defaultProfile: AgentDefaultProfile;
  defaultModelSettings: AgentModelSettings;
  generationConfig: ModelGenerationConfig;
  chatSettings: AgentChatSettings;
  backstory: string;
  communicationStyle: string;
  expertise: string[];
}

export interface StageDefinition {
  id: string;
  order: number;
  badge: string;
  stageTitle?: string;
  description: string;
  stageType?: StageType;
  videoComponent?: string;
  artifactSrc?: string;
  comprehensionQuestions?: ComprehensionQuestion[];
  situationBrief?: SituationBriefData;
  turnConfig: TurnConfig;
  channelType: "1:1" | "group";
  agentProfile: AgentProfile;
  postSurvey?: PostSurveyConfig;
}

export interface ScenarioDefinition {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  skillDimensions: string[];
  assessmentConfig: AssessmentConfig;
  systemBase: string;
  stages: StageDefinition[];
}

// --- Legacy-compatible Stage (used by Simulation.tsx) ---

export interface Stage {
  id: string;
  name: string;
  role: string;
  color: string;
  badge: string;
  stageTitle: string;
  desc: string;
  avatar: string;
  systemPrompt: string;
  stageType: StageType;
  videoComponent?: string;
  artifactSrc?: string;
  comprehensionQuestions?: ComprehensionQuestion[];
  situationBrief?: SituationBriefData;
}

// --- Chat ---

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
}

export interface Assessment {
  stage: string;
  userMessage: string;
  aiReply: string;
  responseTimeMs: number;
}

// Per-dimension evaluation from a single stage agent
export interface DimensionEval {
  score: number;       // 1–100
  evidence: string;    // complete sentence(s); "..." only between whole sentences; "" if not demonstrated
  confidence: number;  // 1–100; low when student had little opportunity to show this dimension
}

// Full evaluation output from one stage
export interface StageEvalResult {
  stageId: string;
  badge: string;
  agentName: string;
  dimensions: Record<string, DimensionEval>;
}

// Unified evaluation result — keyed by skillDimension.key, works for all scenarios
export interface EvaluationResult {
  scores: Record<string, number>;
  feedback: string;
  dimensionDetail?: Record<string, {
    score: number;
    quote: string;     // best evidence sentence(s) from highest-confidence stage
    badge: string;     // which stage the quote came from
    narrative: string; // 1–2 sentence evaluator commentary
  }>;
}

/** @deprecated Use EvaluationResult instead */
export interface FeedbackScores {
  analytical: number;
  communication: number;
  ownership: number;
  adaptability: number;
  feedback: string;
}

export interface ChatRequest {
  system: string;
  messages: { role: string; content: string }[];
  maxTokens?: number;
  disableThinking?: boolean;
}

// --- Participant Metadata ---

export interface ParticipantMetadata {
  participantId: string;
  prolificPid: string | null;
  studyId: string | null;
  sessionCode: string | null;
  userAgent: string;
  platform: string;
  language: string;
  screenWidth: number;
  screenHeight: number;
  devicePixelRatio: number;
  touchCapable: boolean;
  timezone: string;
  collectedAt: number;
}

// --- Survey / Profile Types ---

export interface SurveyQuestion {
  id: string;
  type: "likert" | "freetext";
  prompt: string;
  likertLabels?: string[];
}

export interface SurveyResponse {
  questionId: string;
  value: number | string;
  answeredAt: number;
}

export interface PostSurveyConfig {
  questions: SurveyQuestion[];
}

export interface ProfileData {
  displayName: string;
  experienceLevel: string;
  goal: string;
  submittedAt: number;
}

// --- Persistence Layer Types ---

export interface TranscriptEntry {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  responseTimeMs: number | null;
}

export interface Session {
  id: string;
  participantId: string;
  scenarioId: string;
  startedAt: number;
  completedAt: number | null;
  status: "active" | "completed" | "abandoned";
  metadata: ParticipantMetadata | null;
  userEmail: string | null;
  userName: string | null;
}

export interface StageTranscript {
  sessionId: string;
  stageId: string;
  entries: TranscriptEntry[];
}

export interface SessionAssessment {
  sessionId: string;
  scores: Record<string, number>;
  feedback: string;
  stageEvals: StageEvalResult[];
  responseTimesMs: number[];
  completedAt: number;
}

// ─── Simulation V2 Schema Types ─────────────────────────────────────────────
// Used by Ridgeline and future simulations. Vela uses the V1 types above.

export type ConversationMode = "llm-only" | "director-actor" | "scripted-only";
export type ArtifactType = "html" | "data-table" | "document" | "none";
export type ProbeClassification = "strong" | "vague" | "conflates" | "off-topic";

export interface KnowledgeConstraints {
  canDo: string[];
  cannotDo: string[];
}

export interface AgentDefinition {
  name: string;
  title: string;
  avatar: string;
  color: string;
  personaPrompt: string;
  assessmentRubric: string;
  pollyVoice?: string;
  knowledgeConstraints?: KnowledgeConstraints;
}

export interface ProbeBranches {
  strong: string;
  vague: string;
  conflates: string;
  "off-topic": string;
}

export interface StructuredProbe {
  id: string;
  topic: string;
  triggerAfterTurn: number;
  evaluatorPrompt: string;
  branches: ProbeBranches;
  followUpInstruction: string;
}

export interface ArtifactDefinition {
  type: ArtifactType;
  title: string;
  src: string;
}

export interface ComprehensionCheckV2 {
  title: string;
  questions: ComprehensionQuestion[];
}

export interface StageV2 {
  id: string;
  order: number;
  title: string;
  badge: string;
  description: string;
  stageType: StageType;
  agentIds: string[];
  situationBrief: SituationBriefData;
  video?: { component: string; scriptRef?: string };
  artifact: ArtifactDefinition | null;
  turnConfig: TurnConfig;
  conversationMode: ConversationMode;
  structuredProbes: StructuredProbe[] | null;
  scriptedClosing?: string;
  actorSystemPrompt?: string;
  constraints: string[];
  comprehensionCheck: ComprehensionCheckV2;
}

export interface FacilitatorKey {
  headwinds?: string[];
  netEffect?: string;
  rubricGuidance: { stage: string; notes: string }[];
}

export interface AssessmentConfigV2 {
  scoringMethod: string;
  evaluatorPrompt: string;
  skillDimensions: SkillDimension[];
  facilitatorKey?: FacilitatorKey;
}

export interface SimulationMeta {
  title: string;
  subtitle?: string;
  role: string;
  organization: string;
  domain: string;
  difficulty: string;
  duration: string;
  audience?: string;
  description: string;
}

export interface SimulationV2 {
  id: string;
  version: string;
  meta: SimulationMeta;
  agents: Record<string, AgentDefinition>;
  stages: StageV2[];
  assessmentConfig: AssessmentConfigV2;
}

// Runtime-ready stage (after mapping from SimulationV2)
export interface StageV2Runtime extends StageV2 {
  agent: AgentDefinition; // primary agent (agentIds[0]) resolved
}

// Per-probe classification result collected during Stage 4
export interface ProbeResult {
  probeId: string;
  topic: string;
  classification: ProbeClassification;
}

/** @deprecated Use EvaluationResult instead */
export interface FeedbackScoresV2 {
  scores: Record<string, number>;
  feedback: string;
}

// ─── Cognitive Task Types ─────────────────────────────────────────────────────

export interface TrialData {
  trialIndex: number;
  startedAt: number;       // performance.now()
  respondedAt: number;
  rt: number;
  stimulusOnsetAt: number; // rAF timestamp
}

export interface BanditTrialData extends TrialData {
  taskType: "two-armed-bandit";
  chosenArm: 0 | 1;
  reward: 0 | 1;
  rewardProbabilities: [number, number];
  qValues: [number, number];
}

export interface ARCTrialData extends TrialData {
  taskType: "arc-grid";
  puzzleId: string;
  numEdits: number;
  numAttempts: number;
  correct: boolean;
  gridActions: { x: number; y: number; color: number; timestamp: number }[];
  thinkingTimeMs: number;
}

export interface CognitiveTaskConfig {
  taskId: string;
  taskType: string;
  title: string;
  description: string;
  numTrials: number;
  parameters: Record<string, number>;
  modelType: string;
  instructions: string;
  debrief: string;
}

export interface TaskSummary {
  totalTrials: number;
  completedTrials: number;
  meanRT: number;
  accuracy?: number;
  [key: string]: unknown;
}

export interface TaskResult {
  sessionId: string;
  stageId: string;
  taskType: string;
  trials: TrialData[];
  startedAt: number;
  completedAt: number;
  summary: TaskSummary;
}

export interface ReversalTrialData extends TrialData {
  taskType: "reversal-learning";
  chosenArm: 0 | 1 | 2;
  reward: 0 | 1;
  rewardProbabilities: [number, number, number];
  qValues: [number, number, number];
  phase: "pre-reversal" | "post-reversal";
  trialInPhase: number;
}

export interface TwoStepTrialData extends TrialData {
  taskType: "two-step";
  stage1Choice: 0 | 1;
  stage2State: 0 | 1;
  stage2Choice: 0 | 1;
  transitionType: "common" | "rare";
  reward: 0 | 1;
  rewardProbabilities: number[];
  stage1RT: number;
  stage2RT: number;
}

export interface HanabiAction {
  type: "play" | "discard" | "hint-color" | "hint-value";
  player: "human" | "ai";
  cardIndex?: number;
  hintTarget?: "human" | "ai";
  hintValue?: string;
  timestamp: number;
}

export interface HanabiTrialData extends TrialData {
  taskType: "hanabi";
  turnNumber: number;
  action: HanabiAction;
  gameState: {
    score: number;
    hintsRemaining: number;
    mistakesRemaining: number;
    fireworks: Record<string, number>;
  };
}

export interface ChatTrialData extends TrialData {
  taskType: "chat-simulation";
  stageId: string;
  stageName: string;
  messageCount: number;
  assessmentScores?: EvaluationResult;
}
