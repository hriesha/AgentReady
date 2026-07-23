import { useEffect, useState } from "react";
import { getSkuResult } from "../api/client";
import BeforeAfter from "../components/BeforeAfter";
import GapList from "../components/GapList";
import QuerySimPanel from "../components/QuerySimPanel";
import type { SkuResult } from "../types";

interface SkuDetailProps {
  runId: string;
  skuId: string;
  onBack: () => void;
}

export default function SkuDetail({ runId, skuId, onBack }: SkuDetailProps) {
  const [result, setResult] = useState<SkuResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSkuResult(runId, skuId)
      .then(setResult)
      .catch((fetchError: unknown) =>
        setError(
          fetchError instanceof Error ? fetchError.message : "could not load",
        ),
      );
  }, [runId, skuId]);

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={onBack}
        className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-700 hover:bg-stone-100"
      >
        Back to dashboard
      </button>

      {error && (
        <div className="rounded-lg border border-stone-300 bg-white p-4 text-sm text-stone-700">
          {error}
        </div>
      )}
      {!result && !error && (
        <p className="text-sm text-stone-500">Loading SKU...</p>
      )}

      {result && (
        <>
          <div className="rounded-lg border border-stone-200 bg-white p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-stone-900">
                  {result.title ?? result.sku_id}
                </h2>
                <p className="text-sm text-stone-500">{result.sku_id}</p>
              </div>
              <dl className="flex gap-6 text-sm">
                <div>
                  <dt className="text-stone-500">Readiness</dt>
                  <dd className="text-xl font-semibold text-stone-900">
                    {result.readiness.toFixed(1)}
                  </dd>
                </div>
                <div>
                  <dt className="text-stone-500">Completeness</dt>
                  <dd className="text-xl font-semibold text-stone-900">
                    {result.before_score.toFixed(1)}
                  </dd>
                </div>
                <div>
                  <dt className="text-stone-500">Revenue at risk / month</dt>
                  <dd className="text-xl font-semibold text-stone-900">
                    {result.revenue_at_risk.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                    {result.revenue_is_estimate && (
                      <span className="ml-1 text-xs font-normal text-stone-500">
                        (est.)
                      </span>
                    )}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-stone-500">
                Query simulation
              </h3>
              <QuerySimPanel simulation={result.simulation} />
            </section>
            <section>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-stone-500">
                Gaps, ranked by impact
              </h3>
              <GapList gaps={result.gaps} />
            </section>
          </div>

          <section>
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-stone-500">
              Before and after
            </h3>
            <BeforeAfter
              rewrite={result.rewrite}
              beforeScore={result.before_score}
              afterScore={result.after_score}
            />
          </section>
        </>
      )}
    </div>
  );
}
