import {
  pgTable,
  text,
  timestamp,
  integer,
  jsonb,
  uuid,
} from "drizzle-orm/pg-core";

// --- Auth Tables ---

export const users = pgTable("users", {
  id: uuid("id").defaultRandom().primaryKey(),
  email: text("email").notNull().unique(),
  name: text("name"),
  image: text("image"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const accounts = pgTable("accounts", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: uuid("user_id")
    .references(() => users.id)
    .notNull(),
  provider: text("provider").notNull(),
  providerAccountId: text("provider_account_id").notNull(),
  type: text("type").notNull(),
  accessToken: text("access_token"),
  refreshToken: text("refresh_token"),
  expiresAt: integer("expires_at"),
});

// --- Experiment Tables ---

export const experimentSessions = pgTable("experiment_sessions", {
  id: text("id").primaryKey(),
  userId: uuid("user_id").references(() => users.id),
  participantId: text("participant_id").notNull(),
  scenarioId: text("scenario_id").notNull(),
  startedAt: timestamp("started_at").notNull(),
  completedAt: timestamp("completed_at"),
  status: text("status").notNull().default("active"),
  metadata: jsonb("metadata"),
  userEmail: text("user_email"),
  userName: text("user_name"),
});

export const trials = pgTable("trials", {
  id: uuid("id").defaultRandom().primaryKey(),
  sessionId: text("session_id")
    .references(() => experimentSessions.id)
    .notNull(),
  stageId: text("stage_id").notNull(),
  trialIndex: integer("trial_index").notNull(),
  taskType: text("task_type").notNull(),
  stimulus: jsonb("stimulus"),
  response: jsonb("response"),
  rtMs: integer("rt_ms"),
  outcome: jsonb("outcome"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const cognitiveProfiles = pgTable("cognitive_profiles", {
  id: uuid("id").defaultRandom().primaryKey(),
  sessionId: text("session_id")
    .references(() => experimentSessions.id)
    .notNull(),
  signals: jsonb("signals"),
  centaur: jsonb("centaur"),
  gecco: jsonb("gecco"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const transcripts = pgTable("transcripts", {
  id: uuid("id").defaultRandom().primaryKey(),
  sessionId: text("session_id")
    .references(() => experimentSessions.id)
    .notNull(),
  stageId: text("stage_id").notNull(),
  entries: jsonb("entries").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const surveys = pgTable("surveys", {
  id: uuid("id").defaultRandom().primaryKey(),
  sessionId: text("session_id")
    .references(() => experimentSessions.id)
    .notNull(),
  stageId: text("stage_id").notNull(),
  responses: jsonb("responses").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});
