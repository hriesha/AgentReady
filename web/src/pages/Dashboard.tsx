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
      <div className="rounded-lg border border-stone-300 bg-white p-4 text-sm text-stone-700">
        {error}
      </div>
    );
  }
  if (!results) {
    return <p className="text-sm text-stone-500">Loading audit...</p>;
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
        <p className="mt-3 text-sm text-stone-500">
          Each SKU is scored for completeness, tested against simulated
          shopper queries, and rewritten where the data is weak.
        </p>
      </div>
    );
  }

  if (results.status === "failed") {
    return (
      <div className="rounded-lg border border-stone-300 bg-white p-4 text-sm text-stone-700">
        The audit failed. Upload the catalog and try again.
      </div>
    );
  }

  const aggregates = results.aggregates;
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-stone-200 bg-white p-6">
        <h2 className="text-xl font-semibold text-stone-900">
          Is your catalog ready for AI shoppers?
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-stone-600">
          AI shopping assistants such as ChatGPT shopping, Gemini, and Rufus
          are becoming how people find products. When a product's data is
          thin or vague, an assistant cannot tell whether it answers the
          shopper's question, so it recommends something else. AgentReady
          reads a product catalog and scores every product from 0 to 100 on
          how likely it is to be found, understood, and recommended.
        </p>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-stone-600">
          Each score combines two measurements: how complete the product's
          data is against a weighted rubric of the attributes assistants
          rely on, and how often the product survives simulated shopper
          queries run against its actual data. Click any row in the table to
          see those queries, the ranked data gaps, and a rewritten version
          of the weak attributes.
          {demo &&
            " This page is a saved audit of the catalog of Loomhouse, a fictional home goods shop with 20 products, so you can explore without setting anything up."}{" "}
          To run this on your own storefront's catalog, head to the{" "}
          <a
            href="https://github.com/hriesha/AgentReady"
            className="underline decoration-stone-400 underline-offset-2 hover:text-stone-900"
          >
            GitHub page
          </a>{" "}
          for setup instructions.
        </p>
      </div>
      {aggregates && aggregates.rate_limited_skus > 0 && (
        <div className="rounded-lg border border-stone-300 bg-stone-100 p-4 text-sm text-stone-700">
          Query simulation was temporarily unavailable for{" "}
          {aggregates.rate_limited_skus} of {aggregates.sku_count} SKUs, the
          daily limit was reached. Completeness scores are unaffected.
        </div>
      )}

      {aggregates && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-stone-200 bg-white p-5">
            <ScoreGauge
              score={aggregates.readiness_revenue_weighted}
              label="Catalog readiness, revenue weighted"
            />
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-5">
            <h3 className="text-xs font-medium uppercase tracking-wide text-stone-500">
              Averages
            </h3>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-stone-600">Unweighted readiness</dt>
                <dd className="font-medium text-stone-900">
                  {aggregates.readiness_unweighted.toFixed(1)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-600">SKUs audited</dt>
                <dd className="font-medium text-stone-900">
                  {aggregates.sku_count}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-stone-600">Revenue at risk / month</dt>
                <dd className="font-medium text-stone-900">
                  {aggregates.revenue_at_risk_total.toLocaleString(undefined, {
                    maximumFractionDigits: 0,
                  })}
                </dd>
              </div>
            </dl>
          </div>
          <div className="rounded-lg border border-stone-200 bg-white p-5">
            <h3 className="text-xs font-medium uppercase tracking-wide text-stone-500">
              Most common gaps
            </h3>
            <ul className="mt-3 space-y-2.5 text-sm">
              {aggregates.top_gaps.slice(0, 5).map((gap) => (
                <li key={gap.attribute}>
                  <div className="flex justify-between">
                    <span className="text-stone-700">{gap.attribute}</span>
                    <span className="text-stone-500">
                      {Math.round(gap.share * 100)}% of SKUs
                    </span>
                  </div>
                  <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-stone-200">
                    <div
                      className="h-full"
                      style={{
                        width: `${gap.share * 100}%`,
                        backgroundColor: "#065f46",
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-stone-900">
            SKUs by revenue at risk
          </h2>
          <div className="flex gap-2">
            <a
              href={exportUrl(runId, "audit")}
              className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-100"
            >
              Download audit CSV
            </a>
            <a
              href={exportUrl(runId, "rewritten")}
              className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-100"
            >
              Download rewritten catalog CSV
            </a>
            {!demo && (
              <button
                type="button"
                onClick={onReset}
                className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-100"
              >
                Audit another catalog
              </button>
            )}
          </div>
        </div>
        <div className="mb-3 rounded-lg border border-stone-200 bg-white p-4">
          <dl className="grid grid-cols-1 gap-x-8 gap-y-2 text-xs text-stone-600 sm:grid-cols-2">
            <div>
              <dt className="inline font-medium text-stone-900">Readiness.</dt>{" "}
              <dd className="inline">
                0 to 100, blending how complete the product's data is (60%)
                with how often it surfaced in simulated shopper queries (40%).
              </dd>
            </div>
            <div>
              <dt className="inline font-medium text-stone-900">
                Projected after fixes.
              </dt>{" "}
              <dd className="inline">
                The completeness score if the suggested rewrites are applied.
                The light green segment of the bar is the projected lift.
              </dd>
            </div>
            <div>
              <dt className="inline font-medium text-stone-900">
                Revenue at risk.
              </dt>{" "}
              <dd className="inline">
                Monthly revenue riding on this product, taken from the sales
                columns of the uploaded catalog. (est.) marks a placeholder
                when no sales data was provided.
              </dd>
            </div>
            <div>
              <dt className="inline font-medium text-stone-900">Top gap.</dt>{" "}
              <dd className="inline">
                The missing or vague attribute holding this product back the
                most, weighted by how often simulated queries needed it.
              </dd>
            </div>
          </dl>
        </div>
        <SkuTable results={results.sku_results} onOpen={onOpenSku} />
      </div>
    </div>
  );
}
