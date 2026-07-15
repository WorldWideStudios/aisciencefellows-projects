import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { fileURLToPath } from "url";
import { GoogleGenAI } from "@google/genai";
import type { AnalysisErrorItem, AnalysisResult, LocalizedText, StudentAnalysis } from "./src/types/analysis";

const GEMINI_MODEL = "gemini-2.0-flash";

function getUserApiKey(req: express.Request): string | null {
  const header = req.headers["x-gemini-api-key"];
  const key = Array.isArray(header) ? header[0] : header;
  return key?.trim() || null;
}

function isReferencedFilesTooLargeError(message: string): boolean {
  const normalized = message.toLowerCase();
  return normalized.includes("total referenced files bytes are too large to be read");
}

function resolveMimeType(mimeType: string, fileName: string): string {
  if (mimeType) return mimeType;
  const ext = fileName.split('.').pop()?.toLowerCase();
  const fallbacks: Record<string, string> = {
    pdf: 'application/pdf',
    png: 'image/png',
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    webp: 'image/webp',
    gif: 'image/gif',
    heic: 'image/heic',
  };
  return fallbacks[ext ?? ''] ?? 'application/octet-stream';
}

async function uploadPdfToFileApi(
  genAI: GoogleGenAI,
  file: { data: string; mimeType: string; name: string }
): Promise<{ fileData: { fileUri: string; mimeType: string } }> {
  const buffer = Buffer.from(file.data, 'base64');
  const blob = new Blob([buffer], { type: file.mimeType });

  const uploaded = await genAI.files.upload({
    file: blob,
    config: { mimeType: file.mimeType, displayName: file.name },
  });

  let fileStatus = uploaded;
  while (fileStatus.state === 'PROCESSING') {
    await new Promise((r) => setTimeout(r, 500));
    fileStatus = await genAI.files.get({ name: uploaded.name! });
  }

  if (fileStatus.state === 'FAILED') {
    throw new Error(`File processing failed for ${file.name}`);
  }

  return { fileData: { fileUri: fileStatus.uri!, mimeType: file.mimeType } };
}

interface ModelAnalysisResponse {
  students: Array<{
    name?: unknown;
    score?: unknown;
    legibility?: unknown;
    generalFeedback?: unknown;
    errors?: Array<{
      problemLabel?: unknown;
      message?: unknown;
      explanation?: unknown;
      correction?: unknown;
      topic?: unknown;
    }>;
  }>;
}

function extractJsonPayload(text: string): string {
  const fencedMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (fencedMatch) return fencedMatch[1].trim();

  const firstBrace = text.indexOf("{");
  const lastBrace = text.lastIndexOf("}");
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    return text.slice(firstBrace, lastBrace + 1);
  }

  throw new Error("Model did not return valid JSON.");
}

function repairJsonEscapes(json: string): string {
  let result = "";
  let inString = false;
  let escaped = false;

  for (let i = 0; i < json.length; i += 1) {
    const ch = json[i];

    if (!inString) {
      if (ch === '"') inString = true;
      result += ch;
      continue;
    }

    if (escaped) {
      if (ch === "u") {
        const hex = json.slice(i + 1, i + 5);
        if (/^[0-9a-fA-F]{4}$/.test(hex)) {
          result += `\\u${hex}`;
          i += 4;
        } else {
          result += "\\\\u";
        }
      } else if (/^["\\/bfnrt]$/.test(ch)) {
        result += `\\${ch}`;
      } else {
        result += `\\\\${ch}`;
      }
      escaped = false;
      continue;
    }

    if (ch === "\\") {
      escaped = true;
      continue;
    }

    if (ch === '"') inString = false;
    result += ch;
  }

  if (escaped) result += "\\\\";
  return result;
}

function parseModelJson<T>(text: string): T {
  const payload = extractJsonPayload(text);
  try {
    return JSON.parse(payload) as T;
  } catch {
    return JSON.parse(repairJsonEscapes(payload)) as T;
  }
}

function localized(text: string): LocalizedText {
  return { en: text, ru: text };
}

function normalizeLocalizedText(value: unknown): LocalizedText {
  if (typeof value === "string") return localized(value.trim());
  if (value && typeof value === "object") {
    const candidate = value as { en?: unknown; ru?: unknown };
    const en = typeof candidate.en === "string" ? candidate.en.trim() : "";
    const ru = typeof candidate.ru === "string" ? candidate.ru.trim() : "";
    if (en || ru) return { en: en || ru, ru: ru || en };
  }
  return localized("");
}

function normalizeStudentAnalyses(students: unknown): StudentAnalysis[] {
  return Array.isArray(students)
    ? students.map((student, index) => {
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
              .filter((error) => error.problemLabel.en || error.message.en || error.explanation.en || error.correction.en || error.topic.en)
          : [];

        const generalFeedback = normalizeLocalizedText(candidate.generalFeedback);

        return {
          name: typeof candidate.name === "string" && candidate.name.trim() ? candidate.name.trim() : `Student ${index + 1}`,
          legibility: typeof candidate.legibility === "number" ? candidate.legibility : null,
          generalFeedback: generalFeedback.en || generalFeedback.ru ? generalFeedback : null,
          errors,
          score: typeof candidate.score === "string" && candidate.score.trim() ? candidate.score.trim() : null,
        };
      })
    : [];
}

function needsTranslation(text: LocalizedText, targetLang: "en" | "ru"): boolean {
  const target = targetLang === "ru" ? text.ru : text.en;
  const source = targetLang === "ru" ? text.en : text.ru;
  if (!source.trim()) return false;
  if (!target.trim()) return true;
  if (target !== source) return false;
  return targetLang === "ru" ? /[A-Za-z]/.test(source) : /[А-Яа-яЁё]/.test(source);
}

function needsStudentTranslation(student: StudentAnalysis, targetLang: "en" | "ru"): boolean {
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

function normalizeErrorItem(error: ModelAnalysisResponse["students"][number]["errors"][number]): AnalysisErrorItem {
  return {
    problemLabel: normalizeLocalizedText(error?.problemLabel),
    message: normalizeLocalizedText(error?.message),
    explanation: normalizeLocalizedText(error?.explanation),
    correction: normalizeLocalizedText(error?.correction),
    topic: normalizeLocalizedText(error?.topic),
  };
}

function normalizeStudents(payload: ModelAnalysisResponse): StudentAnalysis[] {
  if (!Array.isArray(payload.students)) {
    throw new Error("Model response is missing the students array.");
  }

  return payload.students.map((student, index) => ({
    name: typeof student?.name === "string" && student.name.trim() ? student.name.trim() : `Student ${index + 1}`,
    score: typeof student?.score === "string" && student.score.trim() ? student.score.trim() : null,
    legibility: typeof student?.legibility === "number"
      ? Math.max(0, Math.min(100, Math.round(student.legibility)))
      : null,
    generalFeedback: (() => {
      const feedback = normalizeLocalizedText(student?.generalFeedback);
      return feedback.en || feedback.ru ? feedback : null;
    })(),
    errors: Array.isArray(student?.errors)
      ? student.errors
          .map(normalizeErrorItem)
          .filter((error) => error.problemLabel.en || error.message.en || error.explanation.en || error.correction.en || error.topic.en)
      : [],
  }));
}

function localizedFieldNeedsBackfill(field: LocalizedText | null | undefined): boolean {
  if (!field) return false;
  if (!field.en.trim() || !field.ru.trim()) return true;
  return field.en.trim() === field.ru.trim();
}

function studentsNeedBackfill(students: StudentAnalysis[]): boolean {
  return students.some((student) =>
    localizedFieldNeedsBackfill(student.generalFeedback) ||
    student.errors.some((error) =>
      localizedFieldNeedsBackfill(error.problemLabel) ||
      localizedFieldNeedsBackfill(error.message) ||
      localizedFieldNeedsBackfill(error.explanation) ||
      localizedFieldNeedsBackfill(error.correction) ||
      localizedFieldNeedsBackfill(error.topic)
    )
  );
}

async function backfillLocalizedStudents(genAI: GoogleGenAI, students: StudentAnalysis[]): Promise<StudentAnalysis[]> {
  if (!studentsNeedBackfill(students)) return students;

  const systemInstruction = `You repair bilingual math-feedback JSON.

Return ONLY valid JSON with this exact shape:
{
  "students": [
    {
      "name": "student name copied exactly",
      "score": "X/Y",
      "legibility": 0,
      "generalFeedback": { "en": "", "ru": "" },
      "errors": [
        {
          "problemLabel": { "en": "", "ru": "" },
          "message": { "en": "", "ru": "" },
          "explanation": { "en": "", "ru": "" },
          "correction": { "en": "", "ru": "" },
          "topic": { "en": "", "ru": "" }
        }
      ]
    }
  ]
}

Rules:
- Preserve student count and order.
- Preserve names, score, legibility, and mathematical meaning.
- Ensure every localized field has BOTH a good English value and a good Russian value.
- If one side is missing or duplicated from the other side, translate it.
- Keep LaTeX unchanged where present.
- Do not invent new mistakes or alter grading.`;

  const response = await genAI.models.generateContent({
    model: GEMINI_MODEL,
    contents: [{
      role: "user",
      parts: [{ text: JSON.stringify({ students }) }],
    }],
    config: { systemInstruction },
  });

  const payload = parseModelJson<ModelAnalysisResponse>(response.text || "");
  return normalizeStudents(payload);
}

function formatStudentRawText(students: StudentAnalysis[], lang: "en" | "ru" = "en"): string {
  return students.map((student) => {
    const errorsBlock = student.errors.length
      ? student.errors.map((error) => {
          const problemLabel = lang === "ru" ? error.problemLabel.ru : error.problemLabel.en;
          const messageText = lang === "ru" ? error.message.ru : error.message.en;
          const explanationText = lang === "ru" ? error.explanation.ru : error.explanation.en;
          const correctionText = lang === "ru" ? error.correction.ru : error.correction.en;
          const topicText = lang === "ru" ? error.topic.ru : error.topic.en;
          const prefix = problemLabel ? `${problemLabel}: ` : "";
          const message = `${prefix}${messageText}`.trim();
          const parts = [`- ${message}`];
          if (explanationText) parts.push(`Explanation: ${explanationText}`);
          if (correctionText) parts.push(`Correction: ${correctionText}`);
          if (topicText) parts.push(`Topic: ${topicText}`);
          return parts.join(" ");
        }).join("\n")
      : "No errors found";

    return [
      `Name: ${student.name}`,
      `Score: ${student.score ?? "N/A"}`,
      `Legibility: ${student.legibility ?? "N/A"}`,
      `General Feedback: ${student.generalFeedback ? (lang === "ru" ? student.generalFeedback.ru : student.generalFeedback.en) : ""}`,
      "Errors and Corrections:",
      errorsBlock,
    ].join("\n");
  }).join("\n\n---\n\n");
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '200mb' }));

  // API routes
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok" });
  });

  app.post("/api/analyze", async (req, res) => {
    const geminiApiKey = getUserApiKey(req);
    if (!geminiApiKey) {
      res.status(401).json({ error: "Missing Gemini API key. Paste your API key in the app to use the service." });
      return;
    }

    const { assignmentFiles, solutionFiles, lang } = req.body as {
      assignmentFiles: { data: string; mimeType: string; name: string; sizeBytes?: number }[];
      solutionFiles: { data: string; mimeType: string; name: string; sizeBytes?: number }[];
      lang?: 'en' | 'ru';
    };

    if (!assignmentFiles?.length || !solutionFiles?.length) {
      res.status(400).json({ error: "assignmentFiles and solutionFiles are required" });
      return;
    }

    const systemInstruction = `You are an expert mathematics professor. Review each student's solution against the provided assignment.

You are given:
1. The assignment (one or more parts)
2. Student solutions (multiple files in this batch)

For EACH solution file:
1. Find the student's full name on the page. If not found, use the filename.
2. Count the total number of problems in the assignment (Y).
3. Analyze each problem's solution.
4. Count fully correct solutions (X).
5. Identify specific mathematical and logical errors.

IMPORTANT: Ignore handwriting quality and minor formatting issues. Evaluate substance only.

Return ONLY valid JSON with this exact shape:
{
  "students": [
    {
      "name": "Full name found, or filename",
      "score": "X/Y",
      "legibility": 0,
      "generalFeedback": { "en": "English feedback", "ru": "Русский отзыв" },
      "errors": [
        {
          "problemLabel": { "en": "Problem 1", "ru": "Задача 1" },
          "message": { "en": "Describe the specific error", "ru": "Опишите конкретную ошибку" },
          "explanation": { "en": "Briefly explain why the step is wrong and what concept was missed", "ru": "Кратко объясните, почему этот шаг неверен и какое понятие было упущено" },
          "correction": { "en": "Concise correct approach or solution", "ru": "Краткое правильное решение или подход" },
          "topic": { "en": "short topic label", "ru": "краткая тема" }
        }
      ]
    }
  ]
}

Rules:
- Return one student object per solution file, in the same order as the input solution files.
- Use an empty errors array when all problems are correct.
- "legibility" must be an integer from 0 to 100 and assess handwriting clarity only, not content.
- Provide both English and Russian for every localized field.
- "explanation" must be a short paragraph of about 2-3 sentences explaining why the mistake is wrong.
- Use LaTeX ($...$ and $$...$$) for mathematical notation inside localized JSON string values when needed.
- Escape backslashes correctly for JSON string values.
- Be concise.
- Keep the meaning aligned across languages.
- Student names should stay as found in the submission and do not need translation.`;

    const genAI = new GoogleGenAI({ apiKey: geminiApiKey });

    try {
      const parts: { text?: string; inlineData?: { data: string; mimeType: string }; fileData?: { fileUri: string; mimeType: string } }[] = [];

      for (const [index, file] of assignmentFiles.entries()) {
        const mimeType = resolveMimeType(file.mimeType, file.name);
        parts.push({ text: `Assignment Part ${index + 1}: ${file.name}` });
        if (mimeType === 'application/pdf') {
          parts.push(await uploadPdfToFileApi(genAI, { ...file, mimeType }));
        } else {
          parts.push({ inlineData: { data: file.data, mimeType } });
        }
      }

      for (const [index, file] of solutionFiles.entries()) {
        const mimeType = resolveMimeType(file.mimeType, file.name);
        parts.push({ text: `Student Solution File ${index + 1}: ${file.name}` });
        if (mimeType === 'application/pdf') {
          parts.push(await uploadPdfToFileApi(genAI, { ...file, mimeType }));
        } else {
          parts.push({ inlineData: { data: file.data, mimeType } });
        }
      }

      const response = await genAI.models.generateContent({
        model: GEMINI_MODEL,
        contents: [{ role: "user", parts }],
        config: { systemInstruction },
      });

      const modelText = response.text || "";
      const payload = parseModelJson<ModelAnalysisResponse>(modelText);
      const initialStudents = normalizeStudents(payload);
      const students = await backfillLocalizedStudents(genAI, initialStudents);
      const rawText = formatStudentRawText(students, lang === "ru" ? "ru" : "en");

      const legibilityScores: Record<string, number> = {};
      students.forEach((student, idx) => {
        if (student.legibility === null) return;
        const file = solutionFiles[idx];
        const key = file ? file.name : `student_${idx + 1}`;
        legibilityScores[key] = student.legibility;
      });

      const result: AnalysisResult = { rawText, legibilityScores, students };
      res.json(result);
    } catch (err) {
      console.error("Gemini API error:", err);
      const message = err instanceof Error ? err.message : "Analysis failed";
      if (isReferencedFilesTooLargeError(message)) {
        res.status(413).json({
          error: "The selected assignment and solution files are too large for one analysis request. Use fewer files per batch or smaller PDFs.",
        });
        return;
      }
      res.status(500).json({ error: message });
    }
  });

  app.post("/api/translate-analysis", async (req, res) => {
    const apiKey = getUserApiKey(req);
    if (!apiKey) {
      res.status(401).json({ error: "Missing Gemini API key. Paste your API key in the app to use the service." });
      return;
    }

    const { students, targetLang } = req.body as {
      students?: StudentAnalysis[];
      targetLang?: "en" | "ru";
    };

    if (!Array.isArray(students) || !students.length || (targetLang !== "en" && targetLang !== "ru")) {
      res.status(400).json({ error: "students and targetLang are required" });
      return;
    }

    const normalizedStudents = normalizeStudentAnalyses(students);
    if (!normalizedStudents.some((student) => needsStudentTranslation(student, targetLang))) {
      res.json({ students: normalizedStudents });
      return;
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
- Only fill in or improve the ${targetLang === "ru" ? "Russian" : "English"} side of localized fields.
- Do not overwrite a good existing translation in the other language.
- Keep math notation and LaTeX intact.
- Use concise educational wording.`;

    const genAI = new GoogleGenAI({ apiKey });

    try {
      const response = await genAI.models.generateContent({
        model: GEMINI_MODEL,
        contents: [{
          role: "user",
          parts: [{ text: JSON.stringify({ students: normalizedStudents, targetLang }) }],
        }],
        config: { systemInstruction },
      });

      const payload = parseModelJson<{ students?: unknown }>(response.text || "");
      res.json({ students: normalizeStudentAnalyses(payload.students) });
    } catch (err) {
      console.error("Gemini translation error:", err);
      const message = err instanceof Error ? err.message : "Translation failed";
      res.status(500).json({ error: message });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
