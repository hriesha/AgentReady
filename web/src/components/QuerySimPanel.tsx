import type { Simulation } from "../types";
import { UNAVAILABLE } from "../types";

interface QuerySimPanelProps {
  simulation: Simulation;
}

export default function QuerySimPanel({ simulation }: QuerySimPanelProps) {
  if (simulation.status === UNAVAILABLE) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-100 p-4 text-sm text-slate-600">
        Query simulation is temporarily unavailable, the daily limit was
        reached. Completeness scores and gaps are unaffected. Run the audit
        again later to fill this in.
      </div>
    );
  }
  return (
    <div>
      {simulation.surface_rate !== null && (
        <p className="mb-3 text-sm text-slate-600">
          Surfaced in{" "}
          <span className="font-medium text-slate-900">
            {Math.round(simulation.surface_rate * 100)}%
          </span>{" "}
          of simulated shopper queries, weighted by confidence.
        </p>
      )}
      <ul className="space-y-3">
        {simulation.queries.map((query) => (
          <li
            key={query.query}
            className="rounded-lg border border-slate-200 bg-white p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-sm text-slate-900">"{query.query}"</p>
              <span className="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                {query.intent_type}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1 text-slate-700">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{
                    backgroundColor: query.would_surface ? "#0ca30c" : "#d03b3b",
                  }}
                />
                {query.would_surface ? "would surface" : "would not surface"}
              </span>
              <span className="text-slate-500">
                confidence {Math.round(query.confidence * 100)}%
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">{query.reason}</p>
            {query.missing_info.length > 0 && (
              <p className="mt-1 text-xs text-slate-500">
                Needed but not found: {query.missing_info.join(", ")}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
