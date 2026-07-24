import { useEffect, useState } from "react";
import { getMetaOnce } from "./api/client";
import Dashboard from "./pages/Dashboard";
import SkuDetail from "./pages/SkuDetail";
import Upload from "./pages/Upload";

type View =
  | { name: "upload" }
  | { name: "dashboard"; runId: string }
  | { name: "sku"; runId: string; skuId: string };

export default function App() {
  const [view, setView] = useState<View>({ name: "upload" });
  const [demoMode, setDemoMode] = useState(false);

  // Learned in the background only so the upload page can hide the affordances
  // that a saved demo cannot serve. Entering the demo is the button's job, so
  // a slow answer here never holds up the page.
  useEffect(() => {
    getMetaOnce()
      .then((meta) => setDemoMode(meta.demo_mode))
      .catch(() => undefined);
  }, []);

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <h1 className="text-xl font-semibold">AgentReady</h1>
          <p className="text-sm text-stone-500">
            AI shopping agent readiness audit
          </p>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        {view.name === "upload" && (
          <Upload
            onAuditStarted={(runId) => setView({ name: "dashboard", runId })}
          />
        )}
        {view.name === "dashboard" && (
          <Dashboard
            runId={view.runId}
            demo={demoMode}
            onOpenSku={(skuId) =>
              setView({ name: "sku", runId: view.runId, skuId })
            }
            onReset={() => setView({ name: "upload" })}
          />
        )}
        {view.name === "sku" && (
          <SkuDetail
            runId={view.runId}
            skuId={view.skuId}
            onBack={() => setView({ name: "dashboard", runId: view.runId })}
          />
        )}
      </main>
    </div>
  );
}
