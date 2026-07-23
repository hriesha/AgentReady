import type { Completeness } from "../types";

const GROUPS = [
  { status: "ok", label: "Specific", dot: "#0ca30c" },
  { status: "vague", label: "Vague", dot: "#fab219" },
  { status: "missing", label: "Missing", dot: "#d03b3b" },
];

interface AttributeBreakdownProps {
  completeness: Completeness;
}

export default function AttributeBreakdown({
  completeness,
}: AttributeBreakdownProps) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        {GROUPS.map((group) => {
          const attributes = completeness.attributes.filter(
            (attribute) => attribute.status === group.status,
          );
          return (
            <div key={group.status}>
              <h4 className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-stone-500">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: group.dot }}
                />
                {group.label} ({attributes.length})
              </h4>
              <ul className="mt-2 space-y-1 text-sm text-stone-700">
                {attributes.length === 0 && (
                  <li className="text-stone-400">none</li>
                )}
                {attributes.map((attribute) => (
                  <li key={attribute.name} className="flex justify-between gap-2">
                    <span>{attribute.name}</span>
                    <span className="shrink-0 text-stone-400">
                      weight {attribute.weight}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
      <p className="mt-4 text-xs text-stone-400">
        Weight is how much an attribute counts toward the completeness score.
        Specific values earn full weight, vague values earn half, missing
        values earn nothing.
      </p>
    </div>
  );
}
