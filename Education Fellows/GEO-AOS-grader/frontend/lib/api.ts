import type {
  AnalyzeCreated,
  AnalyzePatchPayload,
  AnalyzeStatus,
  ReportOut,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export async function createAnalysis(url: string): Promise<AnalyzeCreated> {
  const resp = await fetch(`${API_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  return handle<AnalyzeCreated>(resp);
}

export async function getAnalysis(id: string): Promise<AnalyzeStatus> {
  const resp = await fetch(`${API_URL}/api/analyze/${id}`, { cache: "no-store" });
  return handle<AnalyzeStatus>(resp);
}

export async function getReport(id: string): Promise<ReportOut> {
  const resp = await fetch(`${API_URL}/api/report/${id}`, { cache: "no-store" });
  return handle<ReportOut>(resp);
}

export async function patchAnalysis(
  id: string,
  payload: AnalyzePatchPayload,
): Promise<AnalyzeCreated> {
  const resp = await fetch(`${API_URL}/api/analyze/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle<AnalyzeCreated>(resp);
}
