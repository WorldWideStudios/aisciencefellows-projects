"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createAnalysis } from "@/lib/api";

export default function UrlForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const trimmed = url.trim();
      const normalized = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
      const { id } = await createAnalysis(normalized);
      router.push(`/analyze/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="w-full max-w-xl space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="example.com or https://example.com"
          className="flex-1 border border-ink/20 bg-cream px-4 py-3 text-base text-ink outline-none transition focus:border-orange"
          required
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="bg-ink px-6 py-3 text-base font-medium text-cream transition-colors hover:bg-orange disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Starting…" : "Analyze"}
        </button>
      </div>
      {error && <p className="text-sm text-orange-red">{error}</p>}
      <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink/50">
        Analysis takes ~15 seconds + ~60 seconds for the report.
      </p>
    </form>
  );
}
