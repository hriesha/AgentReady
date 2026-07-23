import { useCallback, useEffect, useState } from "react";
import { exportUrl, getResults, subscribeProgress } from "../api/client";
import ProgressBar from "../components/ProgressBar";
import ScoreGauge from "../components/ScoreGauge";
import SkuTable from "../components/SkuTable";
import type { ProgressEvent, RunResults } from "../types";

interface DashboardProps {
  runId: string;
  demo?: boolean;
  onOpenSku: (skuId: string) => void;
  onReset: () => void;
}

export default function Dashboard({
  runId,
  demo = false,
  onOpenSku,
  onReset,
}: DashboardProps) {
  const [results, setResults] = useState<RunResults | null>(null);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setResults(await getResults(runId));
    } catch (fetchError) {
      setError(
        fetchError instanceof Error ? fetchError.message : "could not load",
      );
    }
  }, [runId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const status = results?.status;
  useEffect(() => {
    if (status !== "running" && status !== "pending") {
      return;
    }
    return subscribeProgress(
      runId,
      (event) => setProgress(event),
      () => void refresh(),
      () => void refresh(),
    );
  }, [status, runId, refresh]);

  if (error) {
    return (
      <div className="rounded-lg border border-slate-300 bg-white p-4 text-sm text-slate-700">
        {error}
      </div>
    );
  }
  if (!results) {
    return <p className="text-sm text-slate-500">Loading audit...</p>;
  }

  if (results.status === "running" || results.status === "pending") {
    return (
      <div className="mx-auto max-w-xl">
        <ProgressBar
          current={progress?.sku_index ?? 0}
          total={progress?.sku_total ?? results.sku_count}
          label={
            progress?.sku_id
              ? `Auditing ${progress.sku_id}`
              : "Starting the audit"
          }
        />
        <p className="mt-3 text-sm text-slate-500">
          Each SKU is scored for completeness, tested against simulated
          shopper queries, and rewritten where the data is weak.
        </p>
      </div>
    );
  }

  if (results.status === "failed") {
    return (
      <div className="rounded-lg border border-slate-300 bg-white p-4 text-sm text-slate-700">
        The audit failed. Upload the catalog and try again.
      </div>
    );
  }

  const aggregates = results.aggregates;
  return (
    <div className="space-y-6">
      {demo && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600">
          This is a saved demo audit of the bundled sample catalog. Live
          audits run locally, see the README for setup.
        </div>
      )}
      {aggregates && aggregates.rate_limited_skus > 0 && (
        <div className="rounded-lg border border-slate-300 bg-slate-100 p-4 text-sm text-slate-700">
          Query simulation was temporarily unavailable for{" "}
          {aggregates.rate_limited_skus} of {aggregates.sku_count} SKUs, the
          daily limit was reached. Completeness scores are unaffected.
        </div>
      )}

      {aggregates && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <ScoreGauge
              score={aggregates.readiness_revenue_weighted}
              label="Catalog readiness, revenue weighted"
            />
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Averages
            </h3>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-600">Unweighted readiness</dt>
                <dd className="font-medium text-slate-900">
                  {aggregates.readiness_unweighted.toFixed(1)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-600">SKUs audited</dt>
                <dd className="font-medium text-slate-900">
                  {aggregates.sku_count}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-600">Revenue at risk / month</dt>
                <dd className="font-medium text-slate-900">
                  {aggregates.revenue_at_risk_total.toLocaleString(undefined, {
                    maximumFractionDigits: 0,
                  })}
                </dd>
              </div>
            </dl>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Most common gaps
            </h3>
            <ul className="mt-3 space-y-2 text-sm">
              {aggregates.top_gaps.slice(0, 5).map((gap) => (
                <li key={gap.attribute} className="flex justify-between">
                  <span className="text-slate-700">{gap.attribute}</span>
                  <span className="text-slate-500">
                    {Math.round(gap.share * 100)}% of SKUs
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">
            SKUs by revenue at risk
          </h2>
          <div className="flex gap-2">
            <a
              href={exportUrl(runId, "audit")}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
            >
              Download audit CSV
            </a>
            <a
              href={exportUrl(runId, "rewritten")}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
            >
              Download rewritten catalog CSV
            </a>
            {!demo && (
              <button
                type="button"
                onClick={onReset}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
              >
                Audit another catalog
              </button>
            )}
          </div>
        </div>
        <SkuTable results={results.sku_results} onOpen={onOpenSku} />
      </div>
    </div>
  );
}
