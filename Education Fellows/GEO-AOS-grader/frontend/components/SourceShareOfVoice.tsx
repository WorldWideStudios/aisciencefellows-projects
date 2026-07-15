"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { ReportOut, SourceShareEntry } from "@/lib/types";

const BRAND_COLOR = "#16a34a";       // green-600
const COMPETITOR_COLOR = "#2563eb";  // blue-600
const OTHER_COLOR = "#a3a3a3";       // neutral-400

function colorFor(entry: SourceShareEntry): string {
  if (entry.is_brand) return BRAND_COLOR;
  if (entry.is_competitor) return COMPETITOR_COLOR;
  return OTHER_COLOR;
}

interface Props {
  report: ReportOut;
}

export default function SourceShareOfVoice({ report }: Props) {
  const sov = report.source_share_of_voice ?? [];
  if (sov.length === 0) {
    return (
      <section>
        <h2 className="mb-3 text-xl font-semibold">Source Share of Voice</h2>
        <p className="text-sm text-neutral-500">No sources found.</p>
      </section>
    );
  }

  const competitorDomains = new Set((report.competitors ?? []).map((c) => c.domain.toLowerCase()));
  const otherDomains = sov.filter((e) => !e.is_brand && !e.is_competitor).slice(0, 5);
  const chartHeight = Math.max(220, sov.length * 28);

  return (
    <section>
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-xl font-semibold">Source Share of Voice</h2>
        <Legend />
      </div>

      <div className="rounded-xl border border-neutral-200 bg-white p-4">
        <div style={{ width: "100%", height: chartHeight }}>
          <ResponsiveContainer>
            <BarChart data={sov} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 4 }}>
              <XAxis type="number" stroke="#737373" fontSize={12} />
              <YAxis
                type="category"
                dataKey="domain"
                width={160}
                stroke="#737373"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                cursor={{ fill: "rgba(0,0,0,0.04)" }}
                contentStyle={{ borderRadius: 8, border: "1px solid #e5e5e5", fontSize: 12 }}
                formatter={(value: number) => [`${value} citations`, "In sources"]}
                labelFormatter={(label) => label}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {sov.map((entry, idx) => (
                  <Cell key={idx} fill={colorFor(entry)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {otherDomains.length > 0 && (
        <div className="mt-5">
          <p className="mb-2 text-sm font-medium text-neutral-700">Top 5 third-party domains in your niche</p>
          <ul className="flex flex-wrap gap-2">
            {otherDomains.map((d) => (
              <li key={d.domain}>
                <a
                  href={`https://${d.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs text-neutral-700 hover:border-neutral-400"
                >
                  <span>{d.domain}</span>
                  <span className="text-neutral-400">{d.count}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3 text-xs text-neutral-600">
      <LegendDot color={BRAND_COLOR} label="Brand" />
      <LegendDot color={COMPETITOR_COLOR} label="Competitor" />
      <LegendDot color={OTHER_COLOR} label="Other" />
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}
