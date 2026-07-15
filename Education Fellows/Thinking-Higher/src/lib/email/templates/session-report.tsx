import {
  Html,
  Head,
  Body,
  Container,
  Section,
  Heading,
  Text,
  Hr,
  Link,
} from "@react-email/components";

interface SessionReportProps {
  participantName?: string;
  sessionId: string;
  completedAt: string;
  taskType: string;
  summary: {
    totalTrials: number;
    completedTrials: number;
    meanRT: number;
    accuracy?: number;
  };
  scores?: {
    analytical?: number;
    communication?: number;
    ownership?: number;
    adaptability?: number;
  };
  modelFit?: {
    alpha?: number;
    tau?: number;
  };
}

function ProgressBar({ value, label }: { value: number; label: string }) {
  return (
    <div style={{ marginBottom: "12px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "13px",
          color: "#e8e6e0",
          marginBottom: "4px",
        }}
      >
        <span>{label}</span>
        <span style={{ color: "#f0c060" }}>{value}/100</span>
      </div>
      <div
        style={{
          background: "#2a2a32",
          borderRadius: "4px",
          height: "8px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            background: "#f0c060",
            height: "100%",
            width: `${value}%`,
            borderRadius: "4px",
          }}
        />
      </div>
    </div>
  );
}

export default function SessionReport({
  participantName,
  sessionId,
  completedAt,
  taskType,
  summary,
  scores,
  modelFit,
}: SessionReportProps) {
  return (
    <Html>
      <Head />
      <Body
        style={{
          backgroundColor: "#0d0d0f",
          fontFamily: "'IBM Plex Mono', monospace",
          color: "#e8e6e0",
          padding: "24px",
        }}
      >
        <Container
          style={{
            maxWidth: "600px",
            margin: "0 auto",
            backgroundColor: "#16161a",
            borderRadius: "16px",
            border: "1px solid #2a2a32",
            padding: "32px",
          }}
        >
          <Text
            style={{
              fontFamily: "'Syne', sans-serif",
              fontWeight: 700,
              fontSize: "18px",
              color: "#f0c060",
              margin: "0 0 4px",
            }}
          >
            Think<span style={{ color: "#e8e6e0" }}>Higher</span>
          </Text>

          <Heading
            style={{
              fontFamily: "'Syne', sans-serif",
              fontSize: "22px",
              fontWeight: 700,
              color: "#e8e6e0",
              margin: "16px 0 8px",
            }}
          >
            Your Cognitive Profile Report
          </Heading>

          <Text style={{ fontSize: "12px", color: "#6b6a72", margin: "0 0 24px" }}>
            {participantName ? `${participantName} — ` : ""}
            {taskType} | {completedAt} | Session {sessionId.slice(0, 8)}
          </Text>

          <Hr style={{ borderColor: "#2a2a32", margin: "16px 0" }} />

          <Section>
            <Text
              style={{
                fontSize: "10px",
                letterSpacing: "0.15em",
                textTransform: "uppercase" as const,
                color: "#6b6a72",
                margin: "0 0 12px",
              }}
            >
              Performance Summary
            </Text>

            <div
              style={{
                display: "flex",
                gap: "12px",
                marginBottom: "20px",
              }}
            >
              <div
                style={{
                  flex: 1,
                  backgroundColor: "#1e1e24",
                  border: "1px solid #2a2a32",
                  borderRadius: "8px",
                  padding: "12px",
                  textAlign: "center" as const,
                }}
              >
                <Text style={{ fontSize: "20px", fontWeight: 700, color: "#f0c060", margin: 0 }}>
                  {summary.completedTrials}
                </Text>
                <Text style={{ fontSize: "9px", color: "#6b6a72", margin: "4px 0 0", textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
                  Trials
                </Text>
              </div>
              <div
                style={{
                  flex: 1,
                  backgroundColor: "#1e1e24",
                  border: "1px solid #2a2a32",
                  borderRadius: "8px",
                  padding: "12px",
                  textAlign: "center" as const,
                }}
              >
                <Text style={{ fontSize: "20px", fontWeight: 700, color: "#f0c060", margin: 0 }}>
                  {Math.round(summary.meanRT)}ms
                </Text>
                <Text style={{ fontSize: "9px", color: "#6b6a72", margin: "4px 0 0", textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
                  Mean RT
                </Text>
              </div>
              {summary.accuracy !== undefined && (
                <div
                  style={{
                    flex: 1,
                    backgroundColor: "#1e1e24",
                    border: "1px solid #2a2a32",
                    borderRadius: "8px",
                    padding: "12px",
                    textAlign: "center" as const,
                  }}
                >
                  <Text style={{ fontSize: "20px", fontWeight: 700, color: "#f0c060", margin: 0 }}>
                    {Math.round(summary.accuracy * 100)}%
                  </Text>
                  <Text style={{ fontSize: "9px", color: "#6b6a72", margin: "4px 0 0", textTransform: "uppercase" as const, letterSpacing: "0.1em" }}>
                    Accuracy
                  </Text>
                </div>
              )}
            </div>
          </Section>

          {scores && (
            <Section>
              <Text
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.15em",
                  textTransform: "uppercase" as const,
                  color: "#6b6a72",
                  margin: "0 0 12px",
                }}
              >
                Skill Scores
              </Text>
              {scores.analytical !== undefined && (
                <ProgressBar value={scores.analytical} label="Analytical Thinking" />
              )}
              {scores.communication !== undefined && (
                <ProgressBar value={scores.communication} label="Communication" />
              )}
              {scores.ownership !== undefined && (
                <ProgressBar value={scores.ownership} label="Ownership" />
              )}
              {scores.adaptability !== undefined && (
                <ProgressBar value={scores.adaptability} label="Adaptability" />
              )}
            </Section>
          )}

          {modelFit && (
            <>
              <Hr style={{ borderColor: "#2a2a32", margin: "16px 0" }} />
              <Section>
                <Text
                  style={{
                    fontSize: "10px",
                    letterSpacing: "0.15em",
                    textTransform: "uppercase" as const,
                    color: "#6b6a72",
                    margin: "0 0 12px",
                  }}
                >
                  Rescorla-Wagner Model Fit
                </Text>
                {modelFit.alpha !== undefined && (
                  <Text style={{ fontSize: "12px", color: "#e8e6e0", lineHeight: "1.7", margin: "0 0 8px" }}>
                    <strong style={{ color: "#f0c060" }}>Learning rate (alpha): {modelFit.alpha.toFixed(2)}</strong>
                    {" — "}
                    {modelFit.alpha < 0.3
                      ? "You update beliefs gradually, weighting past experience heavily."
                      : modelFit.alpha < 0.6
                        ? "You update beliefs at a moderate pace, balancing past and recent outcomes."
                        : "You respond quickly to recent outcomes, adapting fast to changes."}
                  </Text>
                )}
                {modelFit.tau !== undefined && (
                  <Text style={{ fontSize: "12px", color: "#e8e6e0", lineHeight: "1.7", margin: "0 0 8px" }}>
                    <strong style={{ color: "#f0c060" }}>Exploration (tau): {modelFit.tau.toFixed(1)}</strong>
                    {" — "}
                    {modelFit.tau < 2
                      ? "You explore broadly, trying both options frequently."
                      : modelFit.tau < 5
                        ? "You balance exploration with exploitation."
                        : "You consistently choose the higher-valued option."}
                  </Text>
                )}
              </Section>
            </>
          )}

          <Hr style={{ borderColor: "#2a2a32", margin: "16px 0" }} />

          <Section style={{ textAlign: "center" as const }}>
            <Link
              href={`https://thinkhigher.vercel.app/history/${sessionId}`}
              style={{
                display: "inline-block",
                backgroundColor: "#f0c060",
                color: "#0d0d0f",
                padding: "10px 24px",
                borderRadius: "8px",
                fontWeight: 600,
                fontSize: "12px",
                textDecoration: "none",
              }}
            >
              View Detailed Results
            </Link>
          </Section>

          <Hr style={{ borderColor: "#2a2a32", margin: "24px 0 16px" }} />

          <Text
            style={{
              fontSize: "10px",
              color: "#6b6a72",
              textAlign: "center" as const,
              margin: 0,
            }}
          >
            Powered by ThinkHigher — Cognitive Science Learning Platform
          </Text>
        </Container>
      </Body>
    </Html>
  );
}
