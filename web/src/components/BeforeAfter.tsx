import type { Rewrite } from "../types";
import { UNAVAILABLE } from "../types";

interface BeforeAfterProps {
  rewrite: Rewrite;
  beforeScore: number;
  afterScore: number | null;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "";
  }
  if (Array.isArray(value)) {
    return value.map(String).join(", ");
  }
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key}: ${String(item)}`)
      .join(", ");
  }
  return String(value);
}

export default function BeforeAfter({
  rewrite,
  beforeScore,
  afterScore,
}: BeforeAfterProps) {
  if (rewrite.status === UNAVAILABLE) {
    return (
      <div className="rounded-lg border border-stone-200 bg-stone-100 p-4 text-sm text-stone-600">
        Attribute rewriting is temporarily unavailable, the daily limit was
        reached. Run the audit again later to fill this in.
      </div>
    );
  }
  if (rewrite.outcomes.length === 0) {
    return (
      <p className="text-sm text-stone-500">
        Nothing to rewrite, every attribute is already specific.
      </p>
    );
  }
  return (
    <div>
      {afterScore !== null && (
        <p className="mb-3 text-sm text-stone-600">
          Completeness {beforeScore.toFixed(1)} now, projected{" "}
          <span className="font-medium text-stone-900">
            {afterScore.toFixed(1)}
          </span>{" "}
          after applying the rewrites, a lift of{" "}
          {(afterScore - beforeScore).toFixed(1)} points.
        </p>
      )}
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-stone-200 text-left text-xs uppercase tracking-wide text-stone-500">
              <th className="px-4 py-3 font-medium">Attribute</th>
              <th className="px-4 py-3 font-medium">Original</th>
              <th className="px-4 py-3 font-medium">Rewritten</th>
            </tr>
          </thead>
          <tbody>
            {rewrite.outcomes.map((outcome) => (
              <tr
                key={outcome.attribute}
                className="border-b border-stone-100 align-top last:border-b-0"
              >
                <td className="px-4 py-3 font-medium text-stone-900">
                  {outcome.attribute}
                </td>
                <td className="px-4 py-3 text-stone-600">
                  {formatValue(outcome.original) || (
                    <span className="italic text-stone-400">missing</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {outcome.value !== null ? (
                    <span className="text-stone-900">
                      {formatValue(outcome.value)}
                    </span>
                  ) : (
                    <span className="italic text-stone-500">
                      needs a human: {outcome.needs_human ?? "not derivable"}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
