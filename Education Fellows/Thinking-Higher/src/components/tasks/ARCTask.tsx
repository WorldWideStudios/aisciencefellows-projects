"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import ARCGrid from "./ARCGrid";
import ARCColorPalette from "./ARCColorPalette";

// --- Types ---

interface ARCPuzzle {
  id: string;
  train: { input: number[][]; output: number[][] }[];
  test: { input: number[][]; output: number[][] }[];
}

interface ARCTrialData {
  trialIndex: number;
  startedAt: number;
  respondedAt: number;
  rt: number;
  stimulusOnsetAt: number;
  taskType: "arc-grid";
  puzzleId: string;
  numEdits: number;
  numAttempts: number;
  correct: boolean;
  gridActions: { x: number; y: number; color: number; timestamp: number }[];
  thinkingTimeMs: number;
}

interface TaskSummary {
  totalTrials: number;
  completedTrials: number;
  meanRT: number;
  accuracy?: number;
  [key: string]: unknown;
}

interface ARCTaskProps {
  puzzles: ARCPuzzle[];
  onComplete: (trials: ARCTrialData[], summary: TaskSummary) => void;
}

// --- Helpers ---

function gridsEqual(a: number[][], b: number[][]): boolean {
  if (a.length !== b.length) return false;
  for (let r = 0; r < a.length; r++) {
    if (a[r].length !== b[r].length) return false;
    for (let c = 0; c < a[r].length; c++) {
      if (a[r][c] !== b[r][c]) return false;
    }
  }
  return true;
}

function createEmptyGrid(rows: number, cols: number): number[][] {
  return Array.from({ length: rows }, () => Array(cols).fill(0));
}

// --- Component ---

export default function ARCTask({ puzzles, onComplete }: ARCTaskProps) {
  const [puzzleIndex, setPuzzleIndex] = useState(0);
  const [selectedColor, setSelectedColor] = useState(1);
  const [answerGrid, setAnswerGrid] = useState<number[][]>([]);
  const [attempts, setAttempts] = useState(0);
  const [feedback, setFeedback] = useState<"correct" | "incorrect" | null>(null);
  const [puzzleDone, setPuzzleDone] = useState(false);

  // Data collection refs
  const puzzleStartRef = useRef(performance.now());
  const stimulusOnsetRef = useRef(Date.now());
  const firstEditRef = useRef<number | null>(null);
  const gridActionsRef = useRef<{ x: number; y: number; color: number; timestamp: number }[]>([]);
  const trialsRef = useRef<ARCTrialData[]>([]);

  const MAX_ATTEMPTS = 3;

  const puzzle = puzzles[puzzleIndex];
  const testInput = puzzle.test[0].input;
  const testOutput = puzzle.test[0].output;

  // Initialize answer grid when puzzle changes
  useEffect(() => {
    const output = puzzles[puzzleIndex].test[0].output;
    const rows = output.length;
    const cols = output[0].length;
    setAnswerGrid(createEmptyGrid(rows, cols));
    setAttempts(0);
    setFeedback(null);
    setPuzzleDone(false);
    puzzleStartRef.current = performance.now();
    stimulusOnsetRef.current = Date.now();
    firstEditRef.current = null;
    gridActionsRef.current = [];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [puzzleIndex]);

  const handleCellClick = useCallback(
    (row: number, col: number) => {
      if (puzzleDone) return;

      const now = Date.now();

      // Track first edit for thinking time
      if (firstEditRef.current === null) {
        firstEditRef.current = now;
      }

      // Record action
      gridActionsRef.current.push({
        x: col,
        y: row,
        color: selectedColor,
        timestamp: now,
      });

      // Update grid
      setAnswerGrid((prev) => {
        const newGrid = prev.map((r) => [...r]);
        newGrid[row][col] = selectedColor;
        return newGrid;
      });
    },
    [selectedColor, puzzleDone]
  );

  const handleClearGrid = useCallback(() => {
    if (puzzleDone) return;
    const rows = testOutput.length;
    const cols = testOutput[0].length;
    setAnswerGrid(createEmptyGrid(rows, cols));
    setFeedback(null);
  }, [puzzleDone, testOutput]);

  const recordTrial = useCallback(
    (correct: boolean, attemptCount: number) => {
      const now = performance.now();
      const respondedAt = Date.now();
      const rt = now - puzzleStartRef.current;
      const thinkingTimeMs =
        firstEditRef.current !== null
          ? firstEditRef.current - stimulusOnsetRef.current
          : rt;

      const trial: ARCTrialData = {
        trialIndex: puzzleIndex,
        startedAt: stimulusOnsetRef.current,
        respondedAt,
        rt,
        stimulusOnsetAt: stimulusOnsetRef.current,
        taskType: "arc-grid",
        puzzleId: puzzle.id,
        numEdits: gridActionsRef.current.length,
        numAttempts: attemptCount,
        correct,
        gridActions: [...gridActionsRef.current],
        thinkingTimeMs,
      };

      trialsRef.current.push(trial);
    },
    [puzzleIndex, puzzle.id]
  );

  const handleCheckAnswer = useCallback(() => {
    if (puzzleDone) return;

    const newAttempts = attempts + 1;
    setAttempts(newAttempts);

    const correct = gridsEqual(answerGrid, testOutput);

    if (correct) {
      setFeedback("correct");
      setPuzzleDone(true);
      recordTrial(true, newAttempts);
    } else if (newAttempts >= MAX_ATTEMPTS) {
      setFeedback("incorrect");
      setPuzzleDone(true);
      recordTrial(false, newAttempts);
    } else {
      setFeedback("incorrect");
      // Allow retry -- feedback will clear on next cell click
    }
  }, [puzzleDone, attempts, answerGrid, testOutput, recordTrial]);

  const handleNextPuzzle = useCallback(() => {
    if (puzzleIndex < puzzles.length - 1) {
      setPuzzleIndex(puzzleIndex + 1);
    } else {
      // All puzzles done -- compute summary
      const trials = trialsRef.current;
      const correctCount = trials.filter((t) => t.correct).length;
      const meanRT =
        trials.length > 0
          ? trials.reduce((sum, t) => sum + t.rt, 0) / trials.length
          : 0;

      const summary: TaskSummary = {
        totalTrials: puzzles.length,
        completedTrials: trials.length,
        meanRT,
        accuracy: correctCount / puzzles.length,
      };

      onComplete(trials, summary);
    }
  }, [puzzleIndex, puzzles.length, onComplete]);

  // Clear incorrect feedback when user starts editing again
  useEffect(() => {
    if (feedback === "incorrect" && !puzzleDone) {
      // The feedback will remain visible until next interaction
    }
  }, [feedback, puzzleDone]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 24,
        padding: 24,
        maxWidth: 900,
        margin: "0 auto",
        fontFamily: "'IBM Plex Mono', monospace",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div
          style={{
            fontFamily: "'Syne', sans-serif",
            fontSize: 16,
            fontWeight: 700,
            color: "var(--text)",
          }}
        >
          ARC Pattern Puzzles
        </div>
        <div
          style={{
            fontSize: 12,
            color: "var(--muted)",
            letterSpacing: "0.05em",
          }}
        >
          Puzzle {puzzleIndex + 1} / {puzzles.length}
        </div>
      </div>

      {/* Training Examples */}
      <div>
        <div
          style={{
            fontSize: 10,
            letterSpacing: "0.15em",
            textTransform: "uppercase" as const,
            color: "var(--muted)",
            marginBottom: 12,
            fontWeight: 500,
          }}
        >
          Training Examples
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          {puzzle.train.map((example, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: 12,
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 8,
              }}
            >
              <ARCGrid grid={example.input} label={`Input ${i + 1}`} />
              <div
                style={{
                  fontSize: 20,
                  color: "var(--accent)",
                  fontFamily: "'Syne', sans-serif",
                  fontWeight: 700,
                  padding: "0 4px",
                  flexShrink: 0,
                }}
              >
                &rarr;
              </div>
              <ARCGrid grid={example.output} label={`Output ${i + 1}`} />
            </div>
          ))}
        </div>
      </div>

      {/* Test Section */}
      <div>
        <div
          style={{
            fontSize: 10,
            letterSpacing: "0.15em",
            textTransform: "uppercase" as const,
            color: "var(--muted)",
            marginBottom: 12,
            fontWeight: 500,
          }}
        >
          Test
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 16,
            padding: 12,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 8,
          }}
        >
          <ARCGrid grid={testInput} label="Input" />
          <div
            style={{
              fontSize: 20,
              color: "var(--accent)",
              fontFamily: "'Syne', sans-serif",
              fontWeight: 700,
              padding: "0 4px",
              flexShrink: 0,
              marginTop: 28,
            }}
          >
            &rarr;
          </div>
          <ARCGrid
            grid={answerGrid}
            editable={!puzzleDone}
            selectedColor={selectedColor}
            onCellClick={handleCellClick}
            label="Your Answer"
          />

          {/* Show correct answer after puzzle is done and was wrong */}
          {puzzleDone && !gridsEqual(answerGrid, testOutput) && (
            <>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--muted)",
                  padding: "0 4px",
                  flexShrink: 0,
                  marginTop: 28,
                }}
              >
                correct:
              </div>
              <ARCGrid grid={testOutput} label="Answer" />
            </>
          )}
        </div>
      </div>

      {/* Color Palette */}
      <div>
        <div
          style={{
            fontSize: 10,
            letterSpacing: "0.15em",
            textTransform: "uppercase" as const,
            color: "var(--muted)",
            marginBottom: 8,
            fontWeight: 500,
          }}
        >
          Color Palette
        </div>
        <ARCColorPalette
          selectedColor={selectedColor}
          onSelectColor={setSelectedColor}
        />
      </div>

      {/* Controls + Feedback */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        {!puzzleDone && (
          <>
            <button
              onClick={handleCheckAnswer}
              style={{
                background: "var(--accent)",
                color: "var(--bg)",
                border: "none",
                borderRadius: 8,
                padding: "10px 20px",
                fontFamily: "'Syne', sans-serif",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                letterSpacing: "0.05em",
                transition: "opacity 0.2s",
              }}
            >
              Check Answer
            </button>
            <button
              onClick={handleClearGrid}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                color: "var(--text)",
                borderRadius: 8,
                padding: "10px 20px",
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 11,
                cursor: "pointer",
                letterSpacing: "0.05em",
                transition: "border-color 0.2s",
              }}
            >
              Clear Grid
            </button>
          </>
        )}

        {puzzleDone && (
          <button
            onClick={handleNextPuzzle}
            style={{
              background: "var(--accent)",
              color: "var(--bg)",
              border: "none",
              borderRadius: 8,
              padding: "10px 20px",
              fontFamily: "'Syne', sans-serif",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              letterSpacing: "0.05em",
              transition: "opacity 0.2s",
            }}
          >
            {puzzleIndex < puzzles.length - 1 ? "Next Puzzle \u2192" : "Finish"}
          </button>
        )}

        {/* Feedback message */}
        {feedback && (
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color:
                feedback === "correct"
                  ? "var(--success)"
                  : "var(--danger)",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            {feedback === "correct" ? (
              "Correct!"
            ) : puzzleDone ? (
              "Incorrect -- max attempts reached."
            ) : (
              `Incorrect. ${MAX_ATTEMPTS - attempts} attempt${MAX_ATTEMPTS - attempts !== 1 ? "s" : ""} remaining.`
            )}
          </div>
        )}

        {/* Attempt counter */}
        {!puzzleDone && attempts > 0 && (
          <div
            style={{
              fontSize: 10,
              color: "var(--muted)",
              marginLeft: "auto",
            }}
          >
            Attempt {attempts}/{MAX_ATTEMPTS}
          </div>
        )}
      </div>
    </div>
  );
}
