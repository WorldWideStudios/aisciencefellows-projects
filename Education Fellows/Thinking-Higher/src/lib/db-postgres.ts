import { eq, and } from "drizzle-orm";
import { pgDb } from "./drizzle";
import {
  experimentSessions,
  transcripts as transcriptsTable,
  cognitiveProfiles,
} from "./schema";
import type { DB } from "./db";
import type {
  Session,
  StageTranscript,
  SessionAssessment,
  StageEvalResult,
  TranscriptEntry,
  SurveyResponse,
  ProfileData,
  TaskResult,
  ParticipantMetadata,
} from "./types";

/**
 * Postgres-backed DB implementation using Drizzle ORM + @vercel/postgres.
 *
 * Drop-in replacement for the in-memory DB — same interface, persistent storage.
 * Activated when POSTGRES_URL is set (see db.ts factory comment).
 */
export function createPostgresDB(): DB {
  return {
    // ---- Sessions ----

    async saveSession(session: Session): Promise<void> {
      await pgDb.insert(experimentSessions).values({
        id: session.id,
        participantId: session.participantId,
        scenarioId: session.scenarioId,
        startedAt: new Date(session.startedAt),
        completedAt: session.completedAt ? new Date(session.completedAt) : null,
        status: session.status,
        metadata: (session.metadata ?? null) as unknown as Record<string, unknown>,
        userEmail: session.userEmail ?? null,
        userName: session.userName ?? null,
      });
    },

    async getSession(sessionId: string): Promise<Session | null> {
      const rows = await pgDb
        .select()
        .from(experimentSessions)
        .where(eq(experimentSessions.id, sessionId))
        .limit(1);

      if (rows.length === 0) return null;

      const row = rows[0];
      return {
        id: row.id,
        participantId: row.participantId,
        scenarioId: row.scenarioId,
        startedAt: row.startedAt.getTime(),
        completedAt: row.completedAt ? row.completedAt.getTime() : null,
        status: row.status as Session["status"],
        metadata: (row.metadata as ParticipantMetadata) ?? null,
        userEmail: row.userEmail ?? null,
        userName: row.userName ?? null,
      };
    },

    async updateSession(
      sessionId: string,
      updates: Partial<Session>,
    ): Promise<void> {
      const setClause: Record<string, unknown> = {};

      if (updates.status !== undefined) {
        setClause.status = updates.status;
      }
      if (updates.completedAt !== undefined) {
        setClause.completedAt = updates.completedAt
          ? new Date(updates.completedAt)
          : null;
      }
      if (updates.participantId !== undefined) {
        setClause.participantId = updates.participantId;
      }
      if (updates.scenarioId !== undefined) {
        setClause.scenarioId = updates.scenarioId;
      }

      if (Object.keys(setClause).length > 0) {
        await pgDb
          .update(experimentSessions)
          .set(setClause)
          .where(eq(experimentSessions.id, sessionId));
      }
    },

    // ---- Transcripts ----

    async saveTranscript(
      sessionId: string,
      stageId: string,
      entries: TranscriptEntry[],
    ): Promise<void> {
      await pgDb.insert(transcriptsTable).values({
        sessionId,
        stageId,
        entries: entries as unknown as Record<string, unknown>,
      });
    },

    async getTranscript(
      sessionId: string,
      stageId: string,
    ): Promise<StageTranscript | null> {
      const rows = await pgDb
        .select()
        .from(transcriptsTable)
        .where(
          and(
            eq(transcriptsTable.sessionId, sessionId),
            eq(transcriptsTable.stageId, stageId),
          ),
        )
        .limit(1);

      if (rows.length === 0) return null;

      const row = rows[0];
      return {
        sessionId: row.sessionId,
        stageId: row.stageId,
        entries: row.entries as unknown as TranscriptEntry[],
      };
    },

    // ---- Assessments (stored as cognitive profiles) ----

    async saveAssessment(
      sessionId: string,
      scores: Record<string, number>,
      feedback: string,
      stageEvals: StageEvalResult[],
      responseTimesMs: number[],
    ): Promise<void> {
      await pgDb.insert(cognitiveProfiles).values({
        sessionId,
        signals: { scores, feedback, stageEvals, responseTimesMs, completedAt: Date.now() } as unknown as Record<string, unknown>,
        centaur: null,
        gecco: null,
      });
    },

    async getAssessment(sessionId: string): Promise<SessionAssessment | null> {
      const rows = await pgDb
        .select()
        .from(cognitiveProfiles)
        .where(eq(cognitiveProfiles.sessionId, sessionId))
        .limit(1);

      if (rows.length === 0) return null;

      const signals = rows[0].signals as Record<string, unknown> | null;
      if (!signals) return null;

      return {
        sessionId,
        scores: signals.scores as Record<string, number>,
        feedback: (signals.feedback as string) ?? "",
        stageEvals: (signals.stageEvals as StageEvalResult[]) ?? [],
        responseTimesMs: signals.responseTimesMs as number[],
        completedAt: signals.completedAt as number,
      };
    },

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async saveProfile(sessionId: string, profile: any): Promise<void> {
      await pgDb.insert(cognitiveProfiles).values({
        sessionId,
        signals: profile as unknown as Record<string, unknown>,
        centaur: null,
        gecco: null,
      });
    },

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async getProfile(sessionId: string): Promise<any | null> {
      const rows = await pgDb
        .select()
        .from(cognitiveProfiles)
        .where(eq(cognitiveProfiles.sessionId, sessionId))
        .limit(1);
      if (rows.length === 0) return null;
      return rows[0].signals;
    },

    async saveSurvey(sessionId: string, stageId: string, responses: SurveyResponse[]): Promise<void> {
      await pgDb.insert(transcriptsTable).values({
        sessionId,
        stageId: `survey:${stageId}`,
        entries: responses as unknown as Record<string, unknown>,
      });
    },

    async saveParticipantProfile(sessionId: string, profile: ProfileData): Promise<void> {
      await pgDb
        .update(experimentSessions)
        .set({ metadata: profile as unknown as Record<string, unknown> })
        .where(eq(experimentSessions.id, sessionId));
    },

    async saveTaskResult(result: TaskResult): Promise<void> {
      await pgDb.insert(transcriptsTable).values({
        sessionId: result.sessionId,
        stageId: `task:${result.stageId}`,
        entries: result as unknown as Record<string, unknown>,
      });
    },

    async getTaskResult(sessionId: string, stageId: string): Promise<TaskResult | null> {
      const rows = await pgDb
        .select()
        .from(transcriptsTable)
        .where(
          and(
            eq(transcriptsTable.sessionId, sessionId),
            eq(transcriptsTable.stageId, `task:${stageId}`),
          ),
        )
        .limit(1);
      if (rows.length === 0) return null;
      return rows[0].entries as unknown as TaskResult;
    },
  };
}
