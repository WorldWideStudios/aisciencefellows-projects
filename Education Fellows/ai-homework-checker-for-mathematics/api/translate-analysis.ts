import type { VercelRequest, VercelResponse } from '@vercel/node';
import { GoogleGenAI } from '@google/genai';
import type { LocalizedText, StudentAnalysis } from '../src/types/analysis';
import { normalizeStudentAnalyses } from '../src/services/geminiService';

const MODEL_NAME = 'gemini-2.0-flash';

interface RequestBody {
  students?: StudentAnalysis[];
  targetLang?: 'en' | 'ru';
}

function normalizeLocalizedText(value: unknown): LocalizedText {
  if (typeof value === 'string') return { en: value.trim(), ru: value.trim() };
  if (value && typeof value === 'object') {
    const candidate = value as { en?: unknown; ru?: unknown };
    const en = typeof candidate.en === 'string' ? candidate.en.trim() : '';
    const ru = typeof candidate.ru === 'string' ? candidate.ru.trim() : '';
    if (en || ru) return { en: en || ru, ru: ru || en };
  }
  return { en: '', ru: '' };
}

function needsTranslation(text: LocalizedText, targetLang: 'en' | 'ru'): boolean {
  const target = targetLang === 'ru' ? text.ru : text.en;
  const source = targetLang === 'ru' ? text.en : text.ru;
  if (!source.trim()) return false;
  if (!target.trim()) return true;
  if (target !== source) return false;
  return targetLang === 'ru' ? /[A-Za-z]/.test(source) : /[А-Яа-яЁё]/.test(source);
}

function needsStudentTranslation(student: StudentAnalysis, targetLang: 'en' | 'ru'): boolean {
  if (student.generalFeedback && needsTranslation(normalizeLocalizedText(student.generalFeedback), targetLang)) {
    return true;
  }

  return student.errors.some((error) =>
    needsTranslation(normalizeLocalizedText(error.problemLabel), targetLang) ||
    needsTranslation(normalizeLocalizedText(error.message), targetLang) ||
    needsTranslation(normalizeLocalizedText(error.correction), targetLang) ||
    needsTranslation(normalizeLocalizedText(error.topic), targetLang)
  );
}

function extractJsonPayload(text: string): string {
  const fencedMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (fencedMatch) return fencedMatch[1].trim();

  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    return text.slice(firstBrace, lastBrace + 1);
  }

  throw new Error('Model did not return valid JSON.');
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const headerValue = req.headers['x-gemini-api-key'];
  const apiKey = (Array.isArray(headerValue) ? headerValue[0] : headerValue)?.trim();
  if (!apiKey) {
    return res.status(401).json({ error: 'Missing Gemini API key. Paste your API key in the app to use the service.' });
  }

  const { students, targetLang } = req.body as RequestBody;
  if (!Array.isArray(students) || !students.length || (targetLang !== 'en' && targetLang !== 'ru')) {
    return res.status(400).json({ error: 'students and targetLang are required' });
  }

  const normalizedStudents = normalizeStudentAnalyses(students);
  if (!normalizedStudents.some((student) => needsStudentTranslation(student, targetLang))) {
    return res.json({ students: normalizedStudents });
  }

  const systemInstruction = `You translate structured math feedback JSON.

Return ONLY valid JSON with this exact shape:
{
  "students": [
    {
      "name": "student name copied exactly",
      "score": "X/Y or null",
      "legibility": 0,
      "generalFeedback": { "en": "", "ru": "" },
      "errors": [
        {
          "problemLabel": { "en": "", "ru": "" },
          "message": { "en": "", "ru": "" },
          "correction": { "en": "", "ru": "" },
          "topic": { "en": "", "ru": "" }
        }
      ]
    }
  ]
}

Rules:
- Preserve every existing field and array order.
- Keep student names, scores, and legibility unchanged.
- Only fill in or improve the ${targetLang === 'ru' ? 'Russian' : 'English'} side of localized fields.
- Do not overwrite a good existing translation in the other language.
- Keep math notation and LaTeX intact.
- Use concise educational wording.`;

  const genAI = new GoogleGenAI({ apiKey });

  try {
    const response = await genAI.models.generateContent({
      model: MODEL_NAME,
      contents: [{
        role: 'user',
        parts: [{ text: JSON.stringify({ students: normalizedStudents, targetLang }) }],
      }],
      config: { systemInstruction },
    });

    const payload = JSON.parse(extractJsonPayload(response.text || '')) as { students?: unknown };
    return res.json({ students: normalizeStudentAnalyses(payload.students) });
  } catch (error) {
    console.error('Gemini translation error:', error);
    const message = error instanceof Error ? error.message : 'Translation failed';
    return res.status(500).json({ error: message });
  }
}
