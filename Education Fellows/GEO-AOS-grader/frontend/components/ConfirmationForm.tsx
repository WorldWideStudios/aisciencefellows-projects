"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { patchAnalysis } from "@/lib/api";
import type { AnalyzeStatus, Competitor } from "@/lib/types";

interface Props {
  data: AnalyzeStatus;
}

export default function ConfirmationForm({ data }: Props) {
  const router = useRouter();

  const [brandName, setBrandName] = useState(data.brand_name ?? "");
  const [brandDomain, setBrandDomain] = useState(data.brand_domain ?? "");
  const [aliasesText, setAliasesText] = useState(
    (data.brand_aliases ?? []).join(", "),
  );
  const [competitors, setCompetitors] = useState<Competitor[]>(
    data.competitors ?? [],
  );
  const [prompts, setPrompts] = useState<string[]>(data.prompts ?? []);
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateCompetitor(idx: number, field: keyof Competitor, value: string) {
    setCompetitors((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, [field]: value } : c)),
    );
  }

  function addCompetitor() {
    setCompetitors((prev) => [...prev, { name: "", domain: "" }]);
  }

  function removeCompetitor(idx: number) {
    setCompetitors((prev) => prev.filter((_, i) => i !== idx));
  }

  function updatePrompt(idx: number, value: string) {
    setPrompts((prev) => prev.map((p, i) => (i === idx ? value : p)));
  }

  function addPrompt() {
    setPrompts((prev) => [...prev, ""]);
  }

  function removePrompt(idx: number) {
    setPrompts((prev) => prev.filter((_, i) => i !== idx));
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const aliases = aliasesText
        .split(",")
        .map((a) => a.trim())
        .filter(Boolean);
      const competitorsClean = competitors
        .map((c) => ({ name: c.name.trim(), domain: c.domain.trim().toLowerCase() }))
        .filter((c) => c.name && c.domain);
      const promptsClean = prompts.map((p) => p.trim()).filter(Boolean);

      if (!brandName.trim() || !brandDomain.trim()) {
        throw new Error("Please enter a brand name and domain");
      }
      if (promptsClean.length === 0) {
        throw new Error("At least one search query is required");
      }

      await patchAnalysis(data.id, {
        brand_name: brandName.trim(),
        brand_domain: brandDomain.trim(),
        brand_aliases: aliases,
        competitors: competitorsClean,
        prompts: promptsClean,
        email: email.trim() || null,
      });

      router.push(`/report/${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-8">
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Brand</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name">
            <input
              className="input"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              required
            />
          </Field>
          <Field label="Domain">
            <input
              className="input"
              value={brandDomain}
              onChange={(e) => setBrandDomain(e.target.value)}
              placeholder="example.com"
              required
            />
          </Field>
        </div>
        <Field label="Alternative spellings (comma-separated)">
          <input
            className="input"
            value={aliasesText}
            onChange={(e) => setAliasesText(e.target.value)}
            placeholder="Acme, ACME Inc, Acme Corp"
          />
        </Field>
      </section>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">Competitors</h2>
          <button
            type="button"
            onClick={addCompetitor}
            className="text-sm text-neutral-600 hover:text-neutral-900"
          >
            + add
          </button>
        </div>
        <div className="space-y-2">
          {competitors.map((c, idx) => (
            <div key={idx} className="flex gap-2">
              <input
                className="input flex-1"
                value={c.name}
                onChange={(e) => updateCompetitor(idx, "name", e.target.value)}
                placeholder="Name"
              />
              <input
                className="input flex-1"
                value={c.domain}
                onChange={(e) => updateCompetitor(idx, "domain", e.target.value)}
                placeholder="domain.com"
              />
              <button
                type="button"
                onClick={() => removeCompetitor(idx)}
                className="rounded px-3 text-neutral-400 hover:text-red-600"
                aria-label="Remove"
              >
                ×
              </button>
            </div>
          ))}
          {competitors.length === 0 && (
            <p className="text-sm text-neutral-500">
              No competitors added. Click &lsquo;add&rsquo; to enter them manually.
            </p>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">Search queries</h2>
          <button
            type="button"
            onClick={addPrompt}
            className="text-sm text-neutral-600 hover:text-neutral-900"
          >
            + add
          </button>
        </div>
        <div className="space-y-2">
          {prompts.map((p, idx) => (
            <div key={idx} className="flex gap-2">
              <span className="w-6 select-none pt-2 text-sm text-neutral-400">
                {idx + 1}.
              </span>
              <input
                className="input flex-1"
                value={p}
                onChange={(e) => updatePrompt(idx, e.target.value)}
              />
              <button
                type="button"
                onClick={() => removePrompt(idx)}
                className="rounded px-3 text-neutral-400 hover:text-red-600"
                aria-label="Remove"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Email (optional)</h2>
        <Field label="Where to send the report link">
          <input
            type="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </Field>
      </section>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="border-t border-neutral-200 pt-6">
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-neutral-900 px-6 py-3 text-base font-medium text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {submitting ? "Running…" : "Generate report"}
        </button>
      </div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-sm text-neutral-600">{label}</span>
      {children}
    </label>
  );
}
