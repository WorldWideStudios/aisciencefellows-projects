"use client";

interface CentaurTrialPrediction {
  trialIndex: number;
  pActual: number;
  pDistribution: Record<string, number>;
  nll: number;
  actualChoice: string;
  predictedChoice: string;
}

export interface CentaurComparisonResult {
  taskType: string;
  meanNLL: number;
  trials: CentaurTrialPrediction[];
  predictionAccuracy: number;
  randomBaselineNLL: number;
  rwModelNLL?: number;
  totalLatencyMs: number;
}

interface CentaurComparisonProps {
  result: CentaurComparisonResult | null;
  loading?: boolean;
  taskType: string;
}

function nllColor(nll: number, randomBaseline: number): string {
  if (nll < 0.44) return "var(--accent)"; // Near Centaur paper average
  if (nll < randomBaseline) return "var(--success)";
  return "var(--muted)";
}

function interpretChoices(
  meanNLL: number,
  randomBaselineNLL: number,
  predictionAccuracy: number
): string[] {
  const lines: string[] = [];
  if (meanNLL < randomBaselineNLL) {
    lines.push(
      "Your choices were more predictable than random — you followed a consistent strategy."
    );
  }
  if (predictionAccuracy > 0.7) {
    lines.push(
      "Centaur predicted your choices with high accuracy, suggesting your behavior closely matches typical human patterns."
    );
  } else if (predictionAccuracy < 0.4) {
    lines.push(
      "Your choices diverged from typical human patterns — you may have been exploring more or using an unusual strategy."
    );
  }
  return lines;
}

export default function CentaurComparison({
  result,
  loading,
  taskType,
}: CentaurComparisonProps) {
  if (!result && !loading) return null;

  if (loading && !result) {
    return (
      <div
        style={{
          marginTop: 24,
          padding: 16,
          background: "var(--surface2)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          textAlign: "center",
        }}
      >
        <p
          style={{
            fontSize: "11px",
            color: "var(--muted)",
            fontFamily: "'IBM Plex Mono', monospace",
            letterSpacing: "0.05em",
          }}
        >
          Computing Centaur comparison...
        </p>
      </div>
    );
  }

  if (!result) return null;

  const lastTrials = result.trials.slice(-20);
  const interpretations = interpretChoices(
    result.meanNLL,
    result.randomBaselineNLL,
    result.predictionAccuracy
  );

  return (
    <div style={{ marginTop: 24 }}>
      <div className="task-tag" style={{ marginBottom: 12 }}>
        YOUR CHOICES VS CENTAUR
      </div>

      <p
        style={{
          fontSize: "11px",
          lineHeight: 1.7,
          color: "var(--muted)",
          marginBottom: 16,
        }}
      >
        Centaur is a foundation model of human cognition (Binz et al., Nature
        2025). It predicts how humans typically behave in this exact task.
        Here&apos;s how your choices compare:
      </p>

      {/* Metric cards */}
      <div className="task-stats">
        <div className="task-stat">
          <div
            className="task-stat-value"
            style={{ color: nllColor(result.meanNLL, result.randomBaselineNLL) }}
          >
            {result.meanNLL.toFixed(2)}
          </div>
          <div className="task-stat-label">Your NLL</div>
        </div>
        <div className="task-stat">
          <div className="task-stat-value">
            {result.randomBaselineNLL.toFixed(2)}
          </div>
          <div className="task-stat-label">Random Guessing</div>
        </div>
        {result.rwModelNLL !== undefined && (
          <div className="task-stat">
            <div className="task-stat-value">
              {result.rwModelNLL.toFixed(2)}
            </div>
            <div className="task-stat-label">RW Model</div>
          </div>
        )}
        <div className="task-stat">
          <div
            className="task-stat-value"
            style={{
              color:
                result.predictionAccuracy > 0.7
                  ? "var(--success)"
                  : result.predictionAccuracy < 0.4
                    ? "var(--danger)"
                    : "var(--text)",
            }}
          >
            {(result.predictionAccuracy * 100).toFixed(0)}%
          </div>
          <div className="task-stat-label">Centaur Accuracy</div>
        </div>
      </div>

      {/* Trial-by-trial chart */}
      {lastTrials.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="task-tag" style={{ marginBottom: 8 }}>
            TRIAL-BY-TRIAL PREDICTIONS (LAST {lastTrials.length})
          </div>
          <div
            style={{
              background: "var(--surface2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "14px 14px 10px",
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 3,
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              {lastTrials.map((trial) => {
                const correct =
                  trial.actualChoice === trial.predictedChoice;
                return (
                  <div
                    key={trial.trialIndex}
                    title={`Trial ${trial.trialIndex + 1}: ${correct ? "Predicted correctly" : "Mispredicted"} (p=${trial.pActual.toFixed(2)})`}
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: 3,
                      background: correct
                        ? "var(--success)"
                        : "var(--danger)",
                      opacity: correct ? 1 : 0.75,
                      transition: "opacity 0.15s",
                    }}
                  />
                );
              })}
            </div>
            <div
              style={{
                display: "flex",
                gap: 12,
                marginTop: 8,
                fontSize: "9px",
                fontFamily: "'IBM Plex Mono', monospace",
                color: "var(--muted)",
              }}
            >
              <span>
                <span
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    background: "var(--success)",
                    borderRadius: 2,
                    marginRight: 4,
                    verticalAlign: "middle",
                  }}
                />
                Correct prediction
              </span>
              <span>
                <span
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    background: "var(--danger)",
                    borderRadius: 2,
                    marginRight: 4,
                    verticalAlign: "middle",
                    opacity: 0.75,
                  }}
                />
                Mispredicted
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Interpretation text */}
      {interpretations.length > 0 && (
        <div
          style={{
            background: "var(--surface2)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: 14,
            marginTop: 12,
          }}
        >
          {interpretations.map((text, i) => (
            <p
              key={i}
              style={{
                fontSize: "11px",
                lineHeight: 1.7,
                color: "var(--muted)",
                marginBottom: i < interpretations.length - 1 ? 8 : 0,
              }}
            >
              {text}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
