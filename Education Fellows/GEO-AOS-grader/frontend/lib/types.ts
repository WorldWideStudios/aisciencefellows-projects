export type ReportStatus =
  | "analyzing"
  | "awaiting_confirmation"
  | "generating"
  | "completed"
  | "failed";

export interface Competitor {
  name: string;
  domain: string;
}

export interface AnalyzeStatus {
  id: string;
  status: ReportStatus;
  url: string;
  created_at: string;
  updated_at: string;
  error: string | null;
  brand_name: string | null;
  brand_domain: string | null;
  brand_aliases: string[] | null;
  brand_description: string | null;
  industry: string | null;
  competitors: Competitor[] | null;
  prompts: string[] | null;
}

export interface AnalyzeCreated {
  id: string;
  status: ReportStatus;
}

export interface AnalyzePatchPayload {
  brand_name: string;
  brand_domain: string;
  brand_aliases: string[];
  competitors: Competitor[];
  prompts: string[];
  email?: string | null;
}

export interface SourceShareEntry {
  domain: string;
  count: number;
  is_brand: boolean;
  is_competitor: boolean;
}

export type SentimentValue = "positive" | "neutral" | "negative";

export interface PromptResultOut {
  id: string;
  prompt: string;
  raw_response: string;
  citations: string[];
  brand_cited: boolean;
  brand_mentioned: boolean;
  competitors_cited: string[];
  competitors_mentioned: string[];
  sentiment: SentimentValue | null;
  error: string | null;
}

export interface ReportOut {
  id: string;
  status: ReportStatus;
  url: string;
  created_at: string;
  updated_at: string;
  error: string | null;

  brand_name: string | null;
  brand_domain: string | null;
  brand_aliases: string[] | null;
  brand_description: string | null;
  industry: string | null;
  competitors: Competitor[] | null;
  prompts: string[] | null;

  aeo_score: number | null;
  citation_rate: number | null;
  mention_rate: number | null;
  sentiment_summary: "positive" | "neutral" | "mixed" | "negative" | null;
  source_share_of_voice: SourceShareEntry[] | null;
  prompt_results: PromptResultOut[];
}
