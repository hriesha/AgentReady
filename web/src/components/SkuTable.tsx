import { useMemo, useState } from "react";
import type { SkuResult } from "../types";

type SortKey = "sku_id" | "readiness" | "after_score" | "revenue_at_risk";

interface SkuTableProps {
  results: SkuResult[];
  onOpen: (skuId: string) => void;
}

function formatRevenue(result: SkuResult): string {
  const amount = result.revenue_at_risk.toLocaleString(undefined, {
    maximumFractionDigits: 0,
  });
  return result.revenue_is_estimate ? `${amount} (est.)` : amount;
}

const HEADERS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "sku_id", label: "SKU", numeric: false },
  { key: "readiness", label: "Readiness", numeric: true },
  { key: "after_score", label: "Projected after fixes", numeric: true },
  { key: "revenue_at_risk", label: "Revenue at risk / month", numeric: true },
];

export default function SkuTable({ results, onOpen }: SkuTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("revenue_at_risk");
  const [descending, setDescending] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...results];
    copy.sort((a, b) => {
      const left = a[sortKey];
      const right = b[sortKey];
      let compare: number;
      if (typeof left === "string" || typeof right === "string") {
        compare = String(left ?? "").localeCompare(String(right ?? ""));
      } else {
        compare = (left ?? -1) - (right ?? -1);
      }
      return descending ? -compare : compare;
    });
    return copy;
  }, [results, sortKey, descending]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setDescending((value) => !value);
    } else {
      setSortKey(key);
      setDescending(true);
    }
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-stone-200 text-left text-xs uppercase tracking-wide text-stone-500">
            {HEADERS.map((header) => (
              <th key={header.key} className="px-4 py-3">
                <button
                  type="button"
                  onClick={() => toggleSort(header.key)}
                  className="font-medium hover:text-stone-800"
                >
                  {header.label}
                  {sortKey === header.key ? (descending ? " (desc)" : " (asc)") : ""}
                </button>
              </th>
            ))}
            <th className="px-4 py-3 font-medium">Top gap</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((result) => (
            <tr
              key={result.sku_id}
              onClick={() => onOpen(result.sku_id)}
              className="cursor-pointer border-b border-stone-100 last:border-b-0 hover:bg-stone-50"
            >
              <td className="px-4 py-3">
                <div className="font-medium text-stone-900">{result.sku_id}</div>
                <div className="max-w-xs truncate text-stone-500">
                  {result.title ?? "untitled"}
                </div>
              </td>
              <td className="px-4 py-3 font-medium text-stone-900">
                {result.readiness.toFixed(1)}
              </td>
              <td className="px-4 py-3 text-stone-700">
                {result.after_score === null ? "n/a" : result.after_score.toFixed(1)}
              </td>
              <td className="px-4 py-3 text-stone-700">{formatRevenue(result)}</td>
              <td className="px-4 py-3 text-stone-700">
                {result.gaps.length > 0 ? result.gaps[0].attribute : "none"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
