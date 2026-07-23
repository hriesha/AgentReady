import type {
  Meta,
  ProgressEvent,
  RunResults,
  SkuResult,
  StartResponse,
  UploadResponse,
} from "../types";

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        message = body.detail;
      } else if (body?.detail?.message) {
        message = body.detail.message;
      }
    } catch {
      // keep the status message
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function getMeta(): Promise<Meta> {
  return request<Meta>("/api/meta");
}

export function uploadCatalog(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/api/catalog/upload", {
    method: "POST",
    body: form,
  });
}

export async function uploadSampleCatalog(): Promise<UploadResponse> {
  const response = await fetch(`${API_BASE}/api/sample-catalog`);
  if (!response.ok) {
    throw new Error("could not load the sample catalog");
  }
  const blob = await response.blob();
  const file = new File([blob], "sample_catalog.csv", { type: "text/csv" });
  return uploadCatalog(file);
}

export function startAudit(runId: string): Promise<StartResponse> {
  return request<StartResponse>(`/api/audit/${runId}/start`, { method: "POST" });
}

export function getResults(runId: string): Promise<RunResults> {
  return request<RunResults>(`/api/audit/${runId}`);
}

export function getSkuResult(runId: string, skuId: string): Promise<SkuResult> {
  return request<SkuResult>(
    `/api/audit/${runId}/sku/${encodeURIComponent(skuId)}`,
  );
}

export function exportUrl(runId: string, kind: "audit" | "rewritten"): string {
  return `${API_BASE}/api/audit/${runId}/export/${kind}.csv`;
}

export function subscribeProgress(
  runId: string,
  onProgress: (event: ProgressEvent) => void,
  onDone: (event: ProgressEvent) => void,
  onError?: () => void,
): () => void {
  const source = new EventSource(`${API_BASE}/api/audit/${runId}/stream`);
  source.onmessage = (event) => {
    onProgress(JSON.parse(event.data) as ProgressEvent);
  };
  source.addEventListener("done", (event) => {
    source.close();
    onDone(JSON.parse((event as MessageEvent).data) as ProgressEvent);
  });
  source.onerror = () => {
    source.close();
    onError?.();
  };
  return () => source.close();
}
