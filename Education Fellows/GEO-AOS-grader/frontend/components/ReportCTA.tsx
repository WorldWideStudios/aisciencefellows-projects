"use client";

import { useState } from "react";

export default function ReportCTA() {
  const [copied, setCopied] = useState(false);
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }

  function onSubmitEmail(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitted(true);
  }

  return (
    <section className="print-hide space-y-6 rounded-2xl border border-neutral-200 bg-neutral-50 p-6 sm:p-8">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={copyLink}
          className="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-700"
        >
          {copied ? "Copied ✓" : "Copy link"}
        </button>
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-lg border border-neutral-300 bg-white px-5 py-2.5 text-sm text-neutral-700 transition hover:border-neutral-500"
        >
          Download PDF
        </button>
      </div>

      <div className="border-t border-neutral-200 pt-6">
        <h3 className="text-base font-medium text-neutral-900">Request a deep audit</h3>
        <p className="mt-1 text-sm text-neutral-600">
          Extended report: 50 queries, monthly trends, content recommendations.
          Leave your email and we&apos;ll send the details.
        </p>
        {submitted ? (
          <p className="mt-4 text-sm text-green-700">Thanks! We&apos;ll be in touch within 24 hours.</p>
        ) : (
          <form onSubmit={onSubmitEmail} className="mt-4 flex flex-col gap-2 sm:flex-row">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="input flex-1"
              required
            />
            <button
              type="submit"
              className="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-700"
            >
              Get details
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
