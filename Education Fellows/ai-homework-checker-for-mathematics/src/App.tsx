import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { GraduationCap, Send, Loader2, AlertCircle, RefreshCw, Download, Clock, CheckCircle2, AlertTriangle, XCircle, KeyRound } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import * as XLSX from 'xlsx';
import { FileUpload } from './components/FileUpload';
import { ThemeToggle } from './components/ThemeToggle';
import { analyzeHomework } from './services/geminiService';
import type { AnalysisErrorItem, LocalizedText, StudentAnalysis } from './types/analysis';

const LEGIBILITY_THRESHOLD_DEFAULT = 85;
const MAX_ANALYSIS_BATCH_BYTES = 45 * 1024 * 1024;

type FileStatus = 'pending' | 'processing' | 'done' | 'flagged';
type Lang = 'en' | 'ru';
type UploadFile = { data: string; mimeType: string; name: string; sizeBytes?: number };

const T = {
  en: {
    title: 'AI Homework Checker for Mathematics',
    subtitle: 'Upload the assignment and multiple student solutions to get instant AI-powered mathematical evaluations for each.',
    assignmentLabel: '1. Assignment (PDF or Images)',
    solutionsLabel: '2. Student Solutions (PDF or Images)',
    checkButton: (n: number) => `Check ${n > 0 ? n : ''} Solution${n !== 1 ? 's' : ''}`,
    processingFiles: 'Processing files...',
    startingAnalysis: 'Starting analysis...',
    analyzingBatch: (cur: number, total: number) => `Analyzing batch ${cur} of ${total}...`,
    batchQueue: 'Batch Queue',
    reviewNeeded: 'Review needed',
    analysisFailed: 'Analysis Failed',
    results: 'Results',
    downloadExcel: 'Download Excel',
    newCheck: 'New Check',
    flaggedBannerTitle: (n: number) => `${n} submission${n > 1 ? 's' : ''} flagged for illegible handwriting`,
    flaggedBannerSub: (threshold: number) => `These submissions scored below ${threshold}/100 for legibility — manual review is recommended.`,
    score: 'Score',
    legibility: 'Legibility',
    errorsCorrections: 'Errors & Corrections',
    noErrors: 'No errors found — all problems correct!',
    showExplanation: 'Why This Is Wrong',
    hideExplanation: 'Hide Explanation',
    correction: 'Correction',
    apiKeyLabel: 'Your Gemini API Key',
    apiKeyPlaceholder: 'Paste your Gemini API key',
    apiKeyHelp: 'Get a free key at',
    apiKeyNote: 'Your key is stored only in this browser and used only for your own requests.',
    footer1: '© 2026 AI Homework Checker for Mathematics',
    footer2: 'Powered by Google Gemini 3.1 Pro',
    colName: 'Name',
    colProblemsSolved: 'Problems Solved',
    colErrors: 'Errors',
    colCorrections: 'Corrections',
    swapWarningTitle: 'Files may be in the wrong slots',
    swapWarningBody: 'You uploaded more files as the Assignment than as Student Solutions. Typically, the assignment is 1–2 files and each student submits one file.',
    swapFiles: '↔ Swap Files',
    continueAnyway: 'Continue Anyway',
  },
  ru: {
    title: 'ИИ-Проверщик Домашних Заданий по Математике',
    subtitle: 'Загрузите задание и решения нескольких студентов для мгновенной оценки с помощью ИИ.',
    assignmentLabel: '1. Задание (PDF или изображения)',
    solutionsLabel: '2. Решения учеников (PDF или изображения)',
    checkButton: (n: number) => {
      if (n === 1) return 'Проверить 1 решение';
      if (n >= 2 && n <= 4) return `Проверить ${n} решения`;
      return `Проверить ${n > 0 ? n : ''} решений`;
    },
    processingFiles: 'Обработка файлов...',
    startingAnalysis: 'Начало анализа...',
    analyzingBatch: (cur: number, total: number) => `Анализ пакета ${cur} из ${total}...`,
    batchQueue: 'Очередь обработки',
    reviewNeeded: 'Требует проверки',
    analysisFailed: 'Ошибка анализа',
    results: 'Результаты',
    downloadExcel: 'Скачать Excel',
    newCheck: 'Новая проверка',
    flaggedBannerTitle: (n: number) => `${n} ${n === 1 ? 'работа помечена' : 'работы помечены'} из-за неразборчивого почерка`,
    flaggedBannerSub: (threshold: number) => `Эти работы набрали ниже ${threshold}/100 по разборчивости — рекомендуется ручная проверка.`,
    score: 'Оценка',
    legibility: 'Разборчивость',
    errorsCorrections: 'Ошибки и исправления',
    noErrors: 'Ошибок не найдено — все задачи решены верно!',
    showExplanation: 'Почему Это Неверно',
    hideExplanation: 'Скрыть Объяснение',
    correction: 'Исправление',
    apiKeyLabel: 'Ваш ключ API Gemini',
    apiKeyPlaceholder: 'Вставьте ваш ключ API Gemini',
    apiKeyHelp: 'Получите бесплатный ключ на',
    apiKeyNote: 'Ключ хранится только в этом браузере и используется только для ваших запросов.',
    footer1: '© 2026 ИИ-Проверщик Домашних Заданий по Математике',
    footer2: 'Работает на Google Gemini 3.1 Pro',
    colName: 'Имя',
    colProblemsSolved: 'Решено задач',
    colErrors: 'Ошибки',
    colCorrections: 'Исправления',
    swapWarningTitle: 'Файлы могут быть перепутаны',
    swapWarningBody: 'Вы загрузили больше файлов как Задание, чем как Решения учеников. Обычно задание — 1–2 файла, а каждый ученик сдаёт один файл.',
    swapFiles: '↔ Поменять местами',
    continueAnyway: 'Продолжить всё равно',
  },
} as const;

// Strip markdown bold/italic asterisks for plain-text contexts (Excel, score displays)
const stripAsterisks = (s: unknown) => typeof s === 'string' ? s.replace(/\*+/g, '').trim() : '';

// Extract a human-readable message from Gemini ApiError JSON blobs
function parseApiError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  try {
    const parsed = JSON.parse(raw);
    return parsed?.error?.message ?? raw;
  } catch {
    return raw;
  }
}

function buildResourceLinks(topic: string): { youtube: string; khanAcademy: string } {
  const q = encodeURIComponent(topic);
  return {
    youtube: `https://www.youtube.com/results?search_query=${q}`,
    khanAcademy: `https://www.khanacademy.org/search?page_search_query=${q}`,
  };
}

function sumFileBytes(files: UploadFile[]): number {
  return files.reduce((total, file) => total + (file.sizeBytes ?? 0), 0);
}

function getLocalizedText(text: LocalizedText | string | null | undefined, lang: Lang): string {
  if (!text) return '';
  if (typeof text === 'string') return stripAsterisks(text);
  return stripAsterisks(lang === 'ru' ? text.ru : text.en);
}

function buildErrorText(error: AnalysisErrorItem, lang: Lang): string {
  const label = getLocalizedText(error.problemLabel, lang);
  const message = getLocalizedText(error.message, lang);
  if (label && message) return `${label}: ${message}`;
  return label || message;
}

export default function App() {
  const [lang, setLang] = useState<Lang>('en');
  const t = T[lang];

  const [assignment, setAssignment] = useState<UploadFile[]>([]);
  const [solutions, setSolutions] = useState<UploadFile[]>([]);
  const [swapWarningDismissed, setSwapWarningDismissed] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [studentSections, setStudentSections] = useState<StudentAnalysis[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<string | null>(null);
  const [isProcessingFiles, setIsProcessingFiles] = useState(false);
  // Legibility threshold kept in state (hidden from UI, active in background)
  const [legibilityThreshold] = useState(LEGIBILITY_THRESHOLD_DEFAULT);
  const [fileStatuses, setFileStatuses] = useState<Record<string, FileStatus>>({});
  const [expandedExplanations, setExpandedExplanations] = useState<Record<string, boolean>>({});
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('gemini-api-key') ?? '');

  const handleApiKeyChange = (value: string) => {
    setApiKey(value);
    localStorage.setItem('gemini-api-key', value.trim());
  };

  const likelySwapped = (() => {
    if (!assignment.length || !solutions.length) return false;
    // 1. Assignment has more files than solutions (most common swap signal)
    if (assignment.length > solutions.length) return true;
    // 2. Any assignment filename looks like a student name: two unicode words + .pdf
    const twoWordPdf = /^[\p{L}]+\s[\p{L}]+\.pdf$/iu;
    if (assignment.some(f => twoWordPdf.test(f.name))) return true;
    // 3. Solutions are all images but assignment has multiple PDFs (type inversion)
    const solutionsAllImages = solutions.every(f => f.mimeType.startsWith('image/'));
    const assignmentAllPdfs = assignment.every(f => f.mimeType === 'application/pdf');
    if (solutionsAllImages && assignmentAllPdfs && assignment.length > 1) return true;
    return false;
  })();

  const showSwapWarning = likelySwapped && !swapWarningDismissed;

  const swapFiles = () => {
    const temp = assignment;
    setAssignment(solutions);
    setSolutions(temp);
    setSwapWarningDismissed(false);
  };

  const handleDownloadExcel = () => {
    if (!studentSections.length) return;
    try {
      const data = studentSections.map(({ name, errors, score }) => {
        const correctionsText = errors.length
          ? errors.map(e => {
              const parts = [buildErrorText(e, lang)];
              const correction = getLocalizedText(e.correction, lang);
              if (correction) parts.push(`→ ${correction}`);
              return parts.join('\n');
            }).join('\n\n')
          : '';
        return {
          [t.colName]: stripAsterisks(name),
          [t.colProblemsSolved]: score ?? 'N/A',
          [t.colErrors]: errors.length,
          [t.colCorrections]: correctionsText,
        };
      });

      const worksheet = XLSX.utils.json_to_sheet(data);

      // Auto-size columns based on content
      const colKeys = [t.colName, t.colProblemsSolved, t.colErrors, t.colCorrections];
      const colWidths = colKeys.map(key => {
        const headerLen = key.length;
        const maxDataLen = data.reduce((max, row) => {
          const val = String((row as Record<string, unknown>)[key] ?? '');
          // For multiline cells, use the longest individual line
          const maxLine = val.split('\n').reduce((m, line) => Math.max(m, line.length), 0);
          return Math.max(max, maxLine);
        }, 0);
        return { wch: Math.min(Math.max(headerLen + 2, maxDataLen + 2), 80) };
      });
      worksheet['!cols'] = colWidths;

      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Results');
      const date = new Date().toISOString().split('T')[0];
      XLSX.writeFile(workbook, `homework_results_${date}.xlsx`);
    } catch {
      setError('Failed to generate Excel file');
    }
  };

  const handleCheck = async () => {
    if (assignment.length === 0 || solutions.length === 0) return;

    setIsAnalyzing(true);
    setError(null);
    setResult(null);
    setStudentSections([]);
    setExpandedExplanations({});
    setAnalysisProgress(t.startingAnalysis);

    const initialStatuses: Record<string, FileStatus> = {};
    solutions.forEach(f => { initialStatuses[f.name] = 'pending'; });
    setFileStatuses(initialStatuses);

    try {
      const batchSize = 3;
      let combinedResult = '';
      const combinedStudents: StudentAnalysis[] = [];
      const updatedStatuses = { ...initialStatuses };
      const assignmentBytes = sumFileBytes(assignment);

      for (let i = 0; i < solutions.length; i += batchSize) {
        const batch = solutions.slice(i, i + batchSize);
        const currentBatchNum = Math.floor(i / batchSize) + 1;
        const totalBatches = Math.ceil(solutions.length / batchSize);
        const batchBytes = assignmentBytes + sumFileBytes(batch);

        if (batchBytes > MAX_ANALYSIS_BATCH_BYTES) {
          throw new Error('The selected assignment and solution files are too large for one analysis request. Reduce the PDF size or use fewer files per batch.');
        }

        batch.forEach(f => { updatedStatuses[f.name] = 'processing'; });
        setFileStatuses({ ...updatedStatuses });
        setAnalysisProgress(t.analyzingBatch(currentBatchNum, totalBatches));

        const response = await analyzeHomework(apiKey.trim(), assignment, batch, lang);
        combinedResult += (combinedResult ? '\n\n' : '') + response.rawText;
        combinedStudents.push(...response.students);

        batch.forEach(f => {
          const score = response.legibilityScores[f.name];
          updatedStatuses[f.name] = (score !== undefined && score < legibilityThreshold) ? 'flagged' : 'done';
        });
        setFileStatuses({ ...updatedStatuses });
        setResult(combinedResult);
        setStudentSections([...combinedStudents]);
      }
    } catch (err) {
      setError(parseApiError(err));
      setFileStatuses({});
    } finally {
      setIsAnalyzing(false);
      setAnalysisProgress(null);
    }
  };

  const reset = () => {
    setAssignment([]);
    setSolutions([]);
    setResult(null);
    setStudentSections([]);
    setExpandedExplanations({});
    setError(null);
    setFileStatuses({});
    setSwapWarningDismissed(false);
  };

  const flaggedCount = studentSections.filter(s => s.legibility !== null && s.legibility < legibilityThreshold).length;
  const hasQueue = Object.keys(fileStatuses).length > 0;

  const statusIcon = (status: FileStatus) => {
    switch (status) {
      case 'pending': return <Clock size={14} className="text-slate-400 dark:text-slate-500" />;
      case 'processing': return <Loader2 size={14} className="animate-spin text-amber-500" />;
      case 'done': return <CheckCircle2 size={14} className="text-emerald-500 dark:text-emerald-400" />;
      case 'flagged': return <AlertTriangle size={14} className="text-amber-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8 dark:bg-slate-950">
      <div className="max-w-4xl mx-auto relative">
        {/* Top-right controls: language toggle + theme toggle */}
        <div className="absolute right-0 top-0 sm:-top-1 flex items-center gap-2">
          <button
            onClick={() => setLang(l => l === 'en' ? 'ru' : 'en')}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:border-slate-300 transition-colors dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"
            title="Switch language / Сменить язык"
          >
            {lang === 'en' ? 'RU' : 'EN'}
          </button>
          <ThemeToggle />
        </div>

        {/* Header */}
        <header className="text-center mb-12 pt-12 sm:pt-0">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600 text-white mb-4 shadow-lg shadow-indigo-200 dark:shadow-indigo-900/50"
          >
            <GraduationCap size={32} />
          </motion.div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight dark:text-slate-100" id="main-title">
            {t.title}
          </h1>
          <p className="mt-2 text-slate-500 max-w-md mx-auto dark:text-slate-400">
            {t.subtitle}
          </p>
        </header>

        <main className="space-y-8">
          {/* Gemini API Key */}
          <div className="bg-white rounded-xl border border-slate-100 p-5 dark:bg-slate-900 dark:border-slate-800">
            <label htmlFor="api-key-input" className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 dark:text-slate-400">
              <KeyRound size={12} />
              {t.apiKeyLabel}
            </label>
            <input
              id="api-key-input"
              type="password"
              autoComplete="off"
              placeholder={t.apiKeyPlaceholder}
              value={apiKey}
              onChange={e => handleApiKeyChange(e.target.value)}
              className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
              {t.apiKeyHelp}{' '}
              <a
                href="https://aistudio.google.com/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium"
              >
                aistudio.google.com/apikey
              </a>
              {' '}· {t.apiKeyNote}
            </p>
          </div>

          {/* Upload Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FileUpload
              id="assignment-upload"
              label={t.assignmentLabel}
              onFilesSelect={(files) => { setAssignment(files); setSwapWarningDismissed(false); }}
              onProcessingChange={setIsProcessingFiles}
              multiple={true}
            />
            <FileUpload
              id="solution-upload"
              label={t.solutionsLabel}
              onFilesSelect={(files) => { setSolutions(files); setSwapWarningDismissed(false); }}
              onProcessingChange={setIsProcessingFiles}
              multiple={true}
            />
          </div>

          {/* HIDDEN: Handwriting Legibility Settings card
          — kept commented to preserve future reinstatement; threshold logic active at {LEGIBILITY_THRESHOLD_DEFAULT}
          <div className="bg-white rounded-xl border border-slate-100 overflow-hidden dark:bg-slate-900 dark:border-slate-800">
            <button onClick={() => setShowSettings(s => !s)} ...>
              Handwriting Legibility Settings
            </button>
            <AnimatePresence>
              {showSettings && (
                <motion.div ...>
                  <input type="range" min={0} max={100} value={legibilityThreshold} onChange={...} />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          */}

          {/* Swap Warning Banner */}
          <AnimatePresence>
            {showSwapWarning && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="flex flex-wrap items-start gap-3 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 dark:bg-amber-950/40 dark:border-amber-800 dark:text-amber-200"
              >
                <AlertTriangle size={18} className="shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm">{t.swapWarningTitle}</p>
                  <p className="text-xs mt-0.5 text-amber-700 dark:text-amber-300/90">{t.swapWarningBody}</p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={swapFiles}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-amber-400 text-amber-800 hover:bg-amber-100 dark:border-amber-600 dark:text-amber-200 dark:hover:bg-amber-900/40 transition-colors"
                  >
                    {t.swapFiles}
                  </button>
                  <button
                    onClick={() => setSwapWarningDismissed(true)}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-amber-200 text-amber-900 hover:bg-amber-300 dark:bg-amber-800/60 dark:text-amber-100 dark:hover:bg-amber-800 transition-colors"
                  >
                    {t.continueAnyway}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Action Button */}
          <div className="flex flex-col items-center gap-4">
            <button
              id="check-button"
              onClick={handleCheck}
              disabled={!apiKey.trim() || assignment.length === 0 || solutions.length === 0 || isAnalyzing || isProcessingFiles}
              className={`
                relative flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-white transition-all duration-200
                ${!apiKey.trim() || assignment.length === 0 || solutions.length === 0 || isAnalyzing || isProcessingFiles
                  ? 'bg-slate-300 cursor-not-allowed dark:bg-slate-600'
                  : 'bg-indigo-600 hover:bg-indigo-700 shadow-lg shadow-indigo-100 hover:shadow-indigo-200 active:scale-95 dark:shadow-indigo-900/40 dark:hover:shadow-indigo-800/50'}
              `}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  {analysisProgress || t.analyzingBatch(1, 1)}
                </>
              ) : isProcessingFiles ? (
                <>
                  <Loader2 className="animate-spin" size={20} />
                  {t.processingFiles}
                </>
              ) : (
                <>
                  <Send size={20} />
                  {t.checkButton(solutions.length)}
                </>
              )}
            </button>
          </div>

          {/* Batch Queue */}
          <AnimatePresence>
            {hasQueue && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="bg-white rounded-xl border border-slate-100 p-4 dark:bg-slate-900 dark:border-slate-800"
              >
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 dark:text-slate-400">{t.batchQueue}</p>
                <div className="space-y-1.5">
                  {Object.entries(fileStatuses).map(([name, status], index) => (
                    <div key={`${name || 'file'}-${index}`} className="flex items-center gap-2 text-sm">
                      {statusIcon(status)}
                      <span className={`truncate ${status === 'flagged' ? 'text-amber-700 font-medium dark:text-amber-400' : 'text-slate-600 dark:text-slate-300'}`}>
                        {name}
                      </span>
                      {status === 'flagged' && (
                        <span className="ml-auto text-xs text-amber-600 font-medium shrink-0 dark:text-amber-400">{t.reviewNeeded}</span>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Results Section */}
          <AnimatePresence>
            {error && (
              <motion.div
                key="analysis-error"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-4 rounded-xl bg-red-50 border border-red-100 flex items-start gap-3 text-red-700 dark:bg-red-950/40 dark:border-red-900/80 dark:text-red-300"
                id="error-panel"
              >
                <AlertCircle className="shrink-0 mt-0.5" size={20} />
                <div>
                  <p className="font-semibold">{t.analysisFailed}</p>
                  <p className="text-sm opacity-90">{error}</p>
                </div>
              </motion.div>
            )}

            {result && studentSections.length > 0 && (
              <motion.div
                key="analysis-result"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="bg-white rounded-2xl p-8 shadow-sm border border-slate-100 dark:bg-slate-900 dark:border-slate-800"
                id="result-panel"
              >
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100 dark:border-slate-800">
                  <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2 dark:text-slate-100">
                    <span className="w-2 h-6 bg-indigo-600 rounded-full" />
                    {t.results}
                  </h2>
                  <div className="flex items-center gap-4">
                    <button
                      onClick={handleDownloadExcel}
                      className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      <Download size={16} />
                      {t.downloadExcel}
                    </button>
                    <button
                      onClick={reset}
                      className="text-slate-400 hover:text-indigo-600 transition-colors flex items-center gap-1 text-sm font-medium dark:text-slate-500 dark:hover:text-indigo-400"
                      id="reset-button"
                    >
                      <RefreshCw size={14} />
                      {t.newCheck}
                    </button>
                  </div>
                </div>

                {/* Illegibility Summary Banner */}
                {flaggedCount > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6 flex items-start gap-3 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 dark:bg-amber-950/40 dark:border-amber-800 dark:text-amber-200"
                  >
                    <AlertTriangle size={18} className="shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-sm">{t.flaggedBannerTitle(flaggedCount)}</p>
                      <p className="text-xs mt-0.5 text-amber-700 dark:text-amber-300/90">
                        {t.flaggedBannerSub(legibilityThreshold)}
                      </p>
                    </div>
                  </motion.div>
                )}

                <div className="space-y-6">
                  {studentSections.map((section, index) => {
                    const { name, legibility, errors, score } = section;
                    const isFlagged = legibility !== null && legibility < legibilityThreshold;

                    return (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className={`rounded-xl border transition-all duration-200 overflow-hidden ${
                          isFlagged
                            ? 'border-amber-300 dark:border-amber-700'
                            : 'border-slate-200 dark:border-slate-700'
                        }`}
                      >
                        {/* Card Header */}
                        <div className={`px-6 py-4 flex items-center justify-between ${
                          isFlagged
                            ? 'bg-amber-50 dark:bg-amber-950/30'
                            : 'bg-slate-50 dark:bg-slate-800/40'
                        }`}>
                          <div>
                            <p className="font-semibold text-slate-900 dark:text-slate-100">{stripAsterisks(name)}</p>
                            {score && (
                              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                                {t.score}: <span className="font-medium text-indigo-600 dark:text-indigo-400">{score}</span>
                              </p>
                            )}
                          </div>
                          {isFlagged && (
                            <div className="flex items-center gap-1.5 text-amber-700 text-xs font-medium dark:text-amber-300 bg-amber-100 dark:bg-amber-900/40 px-2.5 py-1 rounded-full">
                              <AlertTriangle size={12} />
                              {t.legibility}: {legibility}/100
                            </div>
                          )}
                        </div>

                        <div className="px-6 pb-6 pt-4 space-y-3 bg-white dark:bg-slate-900">
                          {/* HIDDEN: General Feedback card
                          — logic preserved; removed from display per requirements
                          {generalFeedback && (
                            <div className="flex items-start gap-3 p-4 rounded-lg bg-blue-50 border border-blue-200 dark:bg-blue-950/30 dark:border-blue-800">
                              <MessageSquare size={16} className="shrink-0 mt-0.5 text-blue-600 dark:text-blue-400" />
                              <div>
                                <p className="text-xs font-semibold text-blue-700 dark:text-blue-300 mb-1 uppercase tracking-wide">General Feedback</p>
                                <p className="text-sm text-blue-800 dark:text-blue-200">{generalFeedback}</p>
                              </div>
                            </div>
                          )}
                          */}

                          {/* Per-error cards with underlined mistakes */}
                          {errors.length > 0 ? (
                            <div className="space-y-3">
                              <div className="flex items-center gap-2">
                                <XCircle size={15} className="text-red-500 dark:text-red-400" />
                                <p className="text-xs font-semibold text-red-700 dark:text-red-300 uppercase tracking-wide">
                                  {t.errorsCorrections} ({errors.length})
                                </p>
                              </div>
                              {errors.map((e, ei) => {
                                const explanation = getLocalizedText(e.explanation, lang);
                                const topic = getLocalizedText(e.topic, lang);
                                const correction = getLocalizedText(e.correction, lang);
                                const links = topic ? buildResourceLinks(topic) : null;
                                const explanationKey = `${index}-${ei}`;
                                const isExplanationOpen = expandedExplanations[explanationKey] ?? false;
                                return (
                                  <div
                                    key={ei}
                                    className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30 p-4"
                                  >
                                    {/* Mistake — underlined */}
                                    <div className="text-sm text-red-800 dark:text-red-200 [&>p]:underline [&>p]:decoration-red-400 [&>p]:decoration-1">
                                      <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex, rehypeRaw]}>
                                        {buildErrorText(e, lang)}
                                      </Markdown>
                                    </div>
                                    {explanation && (
                                      <div className="mt-3">
                                        <button
                                          type="button"
                                          onClick={() => setExpandedExplanations((prev) => ({
                                            ...prev,
                                            [explanationKey]: !isExplanationOpen,
                                          }))}
                                          className="text-xs font-semibold text-sky-700 hover:text-sky-800 dark:text-sky-300 dark:hover:text-sky-200 transition-colors"
                                        >
                                          {isExplanationOpen ? t.hideExplanation : t.showExplanation}
                                        </button>
                                        {isExplanationOpen && (
                                          <div className="mt-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900 dark:border-sky-800 dark:bg-sky-950/30 dark:text-sky-100">
                                            <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex, rehypeRaw]}>
                                              {explanation}
                                            </Markdown>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                    {/* Correction */}
                                    {correction && (
                                      <div className="mt-2 text-sm text-slate-700 dark:text-slate-300">
                                        <span className="font-semibold text-emerald-700 dark:text-emerald-400">{t.correction}: </span>
                                        <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex, rehypeRaw]}>
                                          {correction}
                                        </Markdown>
                                      </div>
                                    )}
                                    {/* Topic links */}
                                    {links && topic && (
                                      <div className="mt-2 flex flex-wrap gap-2">
                                        <a
                                          href={links.youtube}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/40 dark:text-red-300 dark:hover:bg-red-900/60 transition-colors font-medium"
                                        >
                                          YouTube: {topic}
                                        </a>
                                        <a
                                          href={links.khanAcademy}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/40 dark:text-green-300 dark:hover:bg-green-900/60 transition-colors font-medium"
                                        >
                                          Khan Academy: {topic}
                                        </a>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <div className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg px-4 py-3">
                              <CheckCircle2 size={16} />
                              {t.noErrors}
                            </div>
                          )}

                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>

        <footer className="mt-16 text-center text-slate-400 text-xs dark:text-slate-500">
          <p>{t.footer1}</p>
          <p className="mt-1 italic">{t.footer2}</p>
        </footer>
      </div>
    </div>
  );
}
