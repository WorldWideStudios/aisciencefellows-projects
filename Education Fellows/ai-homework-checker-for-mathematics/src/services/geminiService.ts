import type { AnalysisResult, LocalizedText, StudentAnalysis } from '../types/analysis';

function stripAsterisks(text: string): string {
  return text.replace(/\*+/g, '').trim();
}

function localized(text: string): LocalizedText {
  return { en: text, ru: text };
}

function normalizeLocalizedText(value: unknown): LocalizedText {
  if (typeof value === 'string') return localized(value.trim());
  if (value && typeof value === 'object') {
    const candidate = value as { en?: unknown; ru?: unknown };
    const en = typeof candidate.en === 'string' ? candidate.en.trim() : '';
    const ru = typeof candidate.ru === 'string' ? candidate.ru.trim() : '';
    if (en || ru) return { en: en || ru, ru: ru || en };
  }
  return localized('');
}

function normalizeStudent(student: unknown, index: number): StudentAnalysis {
  const candidate = (student ?? {}) as {
    name?: unknown;
    legibility?: unknown;
    generalFeedback?: unknown;
    errors?: unknown;
    score?: unknown;
  };

  const errors = Array.isArray(candidate.errors)
    ? candidate.errors
        .map((error) => {
          const errorCandidate = (error ?? {}) as {
            problemLabel?: unknown;
            message?: unknown;
            explanation?: unknown;
            correction?: unknown;
            topic?: unknown;
          };
          return {
            problemLabel: normalizeLocalizedText(errorCandidate.problemLabel),
            message: normalizeLocalizedText(errorCandidate.message),
            explanation: normalizeLocalizedText(errorCandidate.explanation),
            correction: normalizeLocalizedText(errorCandidate.correction),
            topic: normalizeLocalizedText(errorCandidate.topic),
          };
        })
        .filter(error => error.problemLabel.en || error.message.en || error.explanation.en || error.correction.en || error.topic.en)
    : [];

  const generalFeedback = normalizeLocalizedText(candidate.generalFeedback);

  return {
    name: typeof candidate.name === 'string' && candidate.name.trim() ? candidate.name.trim() : `Student ${index + 1}`,
    legibility: typeof candidate.legibility === 'number' ? candidate.legibility : null,
    generalFeedback: generalFeedback.en || generalFeedback.ru ? generalFeedback : null,
    errors,
    score: typeof candidate.score === 'string' && candidate.score.trim() ? candidate.score.trim() : null,
  };
}

function parseLegacyStudentSections(text: string): StudentAnalysis[] {
  return text
    .split(/---/)
    .filter(section => section.trim().length > 0)
    .map((raw, index) => {
      const cleaned = stripAsterisks(raw);
      const nameMatch = cleaned.match(/Name:\s*(.*)/);
      const legMatch = cleaned.match(/Legibility:\s*(\d+)/);
      const feedbackMatch = cleaned.match(/General Feedback:\s*(.*)/);
      const scoreMatch = cleaned.match(/Score:\s*(\d+\/\d+)/);
      const errorsBlockMatch = cleaned.match(/Errors and Corrections:([\s\S]*?)(?=---|$)/i);

      const errorsBlock = errorsBlockMatch ? errorsBlockMatch[1].trim() : '';
      const hasErrors = errorsBlock.length > 0 && !errorsBlock.toLowerCase().startsWith('no errors found');
      const errors = hasErrors
        ? errorsBlock
            .split('\n')
            .filter(line => line.trim().startsWith('-'))
            .map((line) => {
              const text = stripAsterisks(line.replace(/^-\s*/, '').trim());
              const correctionMatch = text.match(/Correction:\s*(.*?)(?:Topic:|$)/i);
              const topicMatch = text.match(/Topic:\s*(.*?)$/i);
              const problemMatch = text.match(/^(.*?):\s*(.*?)(?:Correction:|Topic:|$)/i);
              return {
                problemLabel: localized(problemMatch ? problemMatch[1].trim() : ''),
                message: localized(problemMatch ? problemMatch[2].trim() : text),
                explanation: localized(''),
                correction: localized(correctionMatch ? correctionMatch[1].trim() : ''),
                topic: localized(topicMatch ? topicMatch[1].trim() : ''),
              };
            })
            .filter(error => error.problemLabel.en || error.message.en || error.explanation.en || error.correction.en || error.topic.en)
        : [];

      return {
        name: nameMatch ? nameMatch[1].trim() : `Student ${index + 1}`,
        legibility: legMatch ? parseInt(legMatch[1], 10) : null,
        generalFeedback: feedbackMatch ? localized(feedbackMatch[1].trim()) : null,
        errors,
        score: scoreMatch ? scoreMatch[1].trim() : null,
      };
    });
}

function normalizeAnalysisResult(body: unknown): AnalysisResult {
  const candidate = (body ?? {}) as Partial<AnalysisResult> & { error?: string };
  const rawText = typeof candidate.rawText === 'string' ? candidate.rawText : '';
  const legibilityScores = candidate.legibilityScores && typeof candidate.legibilityScores === 'object'
    ? candidate.legibilityScores
    : {};
  const students = Array.isArray(candidate.students)
    ? candidate.students.map((student, index) => normalizeStudent(student, index))
    : rawText
      ? parseLegacyStudentSections(rawText)
      : [];

  return { rawText, legibilityScores, students };
}

export function normalizeStudentAnalyses(students: unknown): StudentAnalysis[] {
  return Array.isArray(students)
    ? students.map((student, index) => normalizeStudent(student, index))
    : [];
}

export async function analyzeHomework(
  apiKey: string,
  assignmentFiles: { data: string; mimeType: string; name: string; sizeBytes?: number }[],
  solutionFiles: { data: string; mimeType: string; name: string; sizeBytes?: number }[],
  lang: 'en' | 'ru' = 'en'
): Promise<AnalysisResult> {
  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-gemini-api-key': apiKey },
    body: JSON.stringify({ assignmentFiles, solutionFiles, lang }),
  });

  if (res.status === 413) {
    throw new Error('The files are too large to process in one batch. Try using fewer or smaller files.');
  }

  const body = await res.json().catch(() => ({ error: 'Invalid response from server' }));

  if (!res.ok) {
    throw new Error(body.error || `Server error: ${res.status}`);
  }

  return normalizeAnalysisResult(body);
}

export async function translateStudentAnalyses(
  apiKey: string,
  students: StudentAnalysis[],
  targetLang: 'en' | 'ru'
): Promise<StudentAnalysis[]> {
  const res = await fetch('/api/translate-analysis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-gemini-api-key': apiKey },
    body: JSON.stringify({ students, targetLang }),
  });

  const body = await res.json().catch(() => ({ error: 'Invalid response from server' }));

  if (!res.ok) {
    if (res.status === 404) {
      throw new Error('Translation endpoint unavailable. Restart the dev server and try again.');
    }
    throw new Error(body.error || `Server error: ${res.status}`);
  }

  return normalizeStudentAnalyses(body.students);
}
