import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import SkuDetail from "./pages/SkuDetail";
import Upload from "./pages/Upload";

type View =
  | { name: "upload" }
  | { name: "dashboard"; runId: string }
  | { name: "sku"; runId: string; skuId: string };

export default function App() {
  const [view, setView] = useState<View>({ name: "upload" });

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <h1 className="text-xl font-semibold">AgentReady</h1>
          <p className="text-sm text-slate-500">
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
