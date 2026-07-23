import type { Gap } from "../types";

const STATUS_DOTS: Record<string, string> = {
  missing: "#d03b3b",
  vague: "#fab219",
  query_missing: "#ec835a",
};

const STATUS_LABELS: Record<string, string> = {
  missing: "missing",
  vague: "vague",
  query_missing: "failed real queries",
};

interface GapListProps {
  gaps: Gap[];
}

export default function GapList({ gaps }: GapListProps) {
  if (gaps.length === 0) {
    return <p className="text-sm text-slate-500">No gaps found for this SKU.</p>;
  }
  return (
    <ol className="space-y-3">
      {gaps.map((gap, index) => (
        <li
          key={gap.attribute}
          className="rounded-lg border border-slate-200 bg-white p-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">{index + 1}.</span>
              <span className="font-medium text-slate-900">{gap.attribute}</span>
              <span className="flex items-center gap-1 text-xs text-slate-600">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: STATUS_DOTS[gap.status] ?? "#94a3b8" }}
                />
                {STATUS_LABELS[gap.status] ?? gap.status}
              </span>
            </div>
            <span className="text-xs text-slate-500">impact {gap.impact}</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {gap.reason}
            {gap.frequency_in_failed_queries > 0 &&
              `, blocked ${gap.frequency_in_failed_queries} simulated ${
                gap.frequency_in_failed_queries === 1 ? "query" : "queries"
              }`}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Why agents need it: {gap.agent_need}
          </p>
        </li>
      ))}
    </ol>
  );
}
