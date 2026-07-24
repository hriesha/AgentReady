import { useRef, useState } from "react";
import {
  getMetaOnce,
  startAudit,
  uploadCatalog,
  uploadSampleCatalog,
} from "../api/client";
import LoadingBar from "../components/LoadingBar";
import type { UploadResponse } from "../types";

interface UploadProps {
  onAuditStarted: (runId: string) => void;
}

type BusyKind = "sample" | "file";

const BUSY_MESSAGES: Record<BusyKind, string[]> = {
  sample: [
    "Waking up the server",
    "It sleeps when nobody is using it, so the first visit takes a moment",
    "Reading the sample catalog",
    "Matching the columns to the attribute schema",
    "Scoring 20 products against the rubric",
    "Almost there, thanks for waiting",
  ],
  file: [
    "Reading your CSV",
    "Matching the columns to the attribute schema",
    "Coercing prices, sizes, and stock values",
    "Counting the products it found",
  ],
};

export default function Upload({ onAuditStarted }: UploadProps) {
  const [upload, setUpload] = useState<UploadResponse | null>(null);
  const [busy, setBusy] = useState<BusyKind | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (kind: BusyKind, task: Promise<UploadResponse>) => {
    setBusy(kind);
    setError(null);
    setUpload(null);
    try {
      setUpload(await task);
    } catch (uploadError) {
      setError(
        uploadError instanceof Error ? uploadError.message : "upload failed",
      );
    } finally {
      setBusy(null);
    }
  };

  const onFileChosen = (file: File | undefined) => {
    if (file) {
      void handleUpload("file", uploadCatalog(file));
    }
  };

  /**
   * The entry point into the sample audit, and the place the cold start is
   * absorbed. A saved demo cannot accept an upload, so once meta says demo the
   * button opens the stored run instead of posting a catalog it would reject.
   */
  const useSampleCatalog = async () => {
    setBusy("sample");
    setError(null);
    setUpload(null);
    try {
      const meta = await getMetaOnce().catch(() => null);
      if (meta?.demo_mode && meta.demo_run_id) {
        onAuditStarted(meta.demo_run_id);
        return;
      }
      setUpload(await uploadSampleCatalog());
    } catch (sampleError) {
      setError(
        sampleError instanceof Error
          ? sampleError.message
          : "could not load the sample catalog",
      );
    } finally {
      setBusy(null);
    }
  };

  const runAudit = async () => {
    if (!upload) return;
    setStarting(true);
    setError(null);
    try {
      await startAudit(upload.run_id);
      onAuditStarted(upload.run_id);
    } catch (startError) {
      setError(
        startError instanceof Error ? startError.message : "could not start",
      );
      setStarting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h2 className="text-lg font-semibold text-stone-900">
        Audit a product catalog
      </h2>
      <p className="mt-1 text-sm text-stone-600">
        Upload a catalog CSV to score how ready each product is to be found
        and recommended by AI shopping assistants.
      </p>

      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          onFileChosen(event.dataTransfer.files[0]);
        }}
        className={`mt-6 rounded-lg border-2 border-dashed p-10 text-center ${
          dragActive ? "border-stone-500 bg-stone-100" : "border-stone-300 bg-white"
        }`}
      >
        <p className="text-sm text-stone-600">Drop a CSV here, or</p>
        <div className="mt-3 flex items-center justify-center gap-3">
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => inputRef.current?.click()}
            className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700 disabled:opacity-50"
          >
            Choose a file
          </button>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void useSampleCatalog()}
            className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50"
          >
            Use sample catalog
          </button>
        </div>
        <p className="mt-3 text-sm text-stone-500">
          The sample catalog option is for viewing how the product looks, give
          it a couple seconds to start!
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(event) => onFileChosen(event.target.files?.[0])}
        />
        {busy && (
          <div className="mt-6">
            <LoadingBar
              title={
                busy === "sample"
                  ? "Loading the sample catalog"
                  : "Reading your catalog"
              }
              messages={BUSY_MESSAGES[busy]}
            />
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-stone-300 bg-white p-4 text-sm text-stone-700">
          {error}
        </div>
      )}

      {upload && (
        <div className="mt-6 rounded-lg border border-stone-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-stone-900">
              {upload.sku_count} SKUs parsed
            </h3>
            <button
              type="button"
              disabled={starting}
              onClick={() => void runAudit()}
              className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700 disabled:opacity-50"
            >
              {starting ? "Starting..." : "Run audit"}
            </button>
          </div>

          <h4 className="mt-4 text-xs font-medium uppercase tracking-wide text-stone-500">
            Column mapping
          </h4>
          <ul className="mt-2 grid grid-cols-1 gap-1 text-sm sm:grid-cols-2">
            {Object.entries(upload.mapping_report.mapped).map(
              ([source, target]) => (
                <li key={source} className="text-stone-700">
                  <span className="text-stone-500">{source}</span> mapped to{" "}
                  <span className="font-medium">{target}</span>
                </li>
              ),
            )}
          </ul>
          {upload.mapping_report.extra.length > 0 && (
            <p className="mt-3 text-sm text-stone-500">
              Kept as extra attributes:{" "}
              {upload.mapping_report.extra.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
