import { Session, StageTranscript, SessionAssessment, StageEvalResult, TranscriptEntry, SurveyResponse, ProfileData, TaskResult } from "./types";

// --- Database Interface ---
// Implementations can swap between local JSON storage and Vercel Postgres.

export interface DB {
  saveSession(session: Session): Promise<void>;
  getSession(sessionId: string): Promise<Session | null>;
  updateSession(sessionId: string, updates: Partial<Session>): Promise<void>;
  saveTranscript(sessionId: string, stageId: string, entries: TranscriptEntry[]): Promise<void>;
  getTranscript(sessionId: string, stageId: string): Promise<StageTranscript | null>;
  saveAssessment(sessionId: string, scores: Record<string, number>, feedback: string, stageEvals: StageEvalResult[], responseTimesMs: number[]): Promise<void>;
  getAssessment(sessionId: string): Promise<SessionAssessment | null>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  saveProfile(sessionId: string, profile: any): Promise<void>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getProfile(sessionId: string): Promise<any | null>;
  saveSurvey(sessionId: string, stageId: string, responses: SurveyResponse[]): Promise<void>;
  saveParticipantProfile(sessionId: string, profile: ProfileData): Promise<void>;
  saveTaskResult(result: TaskResult): Promise<void>;
  getTaskResult(sessionId: string, stageId: string): Promise<TaskResult | null>;
}

// --- DB Factory ---
// Uses Postgres when POSTGRES_URL is set (production/preview on Vercel),
// falls back to in-memory Maps for local dev without a database.

function createInMemoryDB(): DB {
  const sessions = new Map<string, Session>();
  const transcripts = new Map<string, StageTranscript>();
  const assessments = new Map<string, SessionAssessment>();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const profiles = new Map<string, any>();
  const surveys = new Map<string, SurveyResponse[]>();
  const participantProfiles = new Map<string, ProfileData>();
  const taskResults = new Map<string, TaskResult>();

  function transcriptKey(sessionId: string, stageId: string) {
    return `${sessionId}:${stageId}`;
  }

  return {
    async saveSession(session) {
      sessions.set(session.id, { ...session });
    },
    async getSession(sessionId) {
      return sessions.get(sessionId) ?? null;
    },
    async updateSession(sessionId, updates) {
      const existing = sessions.get(sessionId);
      if (existing) {
        sessions.set(sessionId, { ...existing, ...updates });
      }
    },
    async saveTranscript(sessionId, stageId, entries) {
      transcripts.set(transcriptKey(sessionId, stageId), {
        sessionId, stageId, entries: [...entries],
      });
    },
    async getTranscript(sessionId, stageId) {
      return transcripts.get(transcriptKey(sessionId, stageId)) ?? null;
    },
    async saveAssessment(sessionId, scores, feedback, stageEvals, responseTimesMs) {
      assessments.set(sessionId, {
        sessionId, scores, feedback, stageEvals, responseTimesMs, completedAt: Date.now(),
      });
    },
    async getAssessment(sessionId) {
      return assessments.get(sessionId) ?? null;
    },
    async saveProfile(sessionId, profile) {
      profiles.set(sessionId, profile);
    },
    async getProfile(sessionId) {
      return profiles.get(sessionId) ?? null;
    },
    async saveSurvey(sessionId, stageId, responses) {
      surveys.set(`${sessionId}:${stageId}`, [...responses]);
    },
    async saveParticipantProfile(sessionId, profile) {
      participantProfiles.set(sessionId, { ...profile });
    },
    async saveTaskResult(result) {
      taskResults.set(transcriptKey(result.sessionId, result.stageId), { ...result });
    },
    async getTaskResult(sessionId, stageId) {
      return taskResults.get(transcriptKey(sessionId, stageId)) ?? null;
    },
  };
}

function createDB(): DB {
  if (process.env.POSTGRES_URL) {
    const { createPostgresDB } = require("./db-postgres");
    return createPostgresDB();
  }
  return createInMemoryDB();
}

export const db: DB = createDB();
