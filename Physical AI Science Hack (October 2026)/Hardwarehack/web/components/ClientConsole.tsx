"use client";
// The console reads per-viewer drafts from localStorage, so it renders in the browser only.
import dynamic from "next/dynamic";

const Console = dynamic(() => import("./Console"), {
  ssr: false,
  loading: () => <p className="px-8 py-16 text-ink-soft">Loading the console…</p>,
});

export default function ClientConsole() {
  return <Console />;
}
