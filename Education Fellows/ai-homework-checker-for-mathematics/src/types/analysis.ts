export interface LocalizedText {
  en: string;
  ru: string;
}

export interface AnalysisErrorItem {
  problemLabel: LocalizedText;
  message: LocalizedText;
  explanation: LocalizedText;
  correction: LocalizedText;
  topic: LocalizedText;
}

export interface StudentAnalysis {
  name: string;
  legibility: number | null;
  generalFeedback: LocalizedText | null;
  errors: AnalysisErrorItem[];
  score: string | null;
}

export interface AnalysisResult {
  rawText: string;
  legibilityScores: Record<string, number>;
  students: StudentAnalysis[];
}
