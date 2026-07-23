export interface MappingReport {
  mapped: Record<string, string>;
  extra: string[];
}

export interface UploadResponse {
  run_id: string;
  sku_count: number;
  mapping_report: MappingReport;
}

export interface StartResponse {
  run_id: string;
  status: string;
}

export interface AttributeScore {
  name: string;
  weight: number;
  status: string;
  score: number;
  reason: string;
}

export interface Completeness {
  score: number;
  attributes: AttributeScore[];
  missing: string[];
  vague: string[];
}

export interface QueryResult {
  query: string;
  intent_type: string;
  would_surface: boolean;
  confidence: number;
  missing_info: string[];
  reason: string;
}

export interface Simulation {
  status: string;
  surface_rate: number | null;
  queries: QueryResult[];
}

export interface Gap {
  attribute: string;
  status: string;
  weight: number;
  frequency_in_failed_queries: number;
  impact: number;
  reason: string;
  agent_need: string;
}

export interface RewriteOutcome {
  attribute: string;
  original: unknown;
  value: unknown;
  needs_human: string | null;
}

export interface Rewrite {
  status: string;
  outcomes: RewriteOutcome[];
}

export interface SkuResult {
  sku_id: string;
  title: string | null;
  revenue_at_risk: number;
  revenue_is_estimate: boolean;
  readiness: number;
  before_score: number;
  after_score: number | null;
  completeness: Completeness;
  simulation: Simulation;
  gaps: Gap[];
  rewrite: Rewrite;
}

export interface CatalogGap {
  attribute: string;
  sku_count: number;
  share: number;
  total_impact: number;
}

export interface Aggregates {
  sku_count: number;
  readiness_revenue_weighted: number;
  readiness_unweighted: number;
  revenue_at_risk_total: number;
  rate_limited_skus: number;
  top_gaps: CatalogGap[];
}

export interface RunResults {
  run_id: string;
  status: string;
  sku_count: number;
  mapping_report: MappingReport;
  aggregates: Aggregates | null;
  sku_results: SkuResult[];
}

export interface Meta {
  demo_mode: boolean;
  demo_run_id: string | null;
}

export interface ProgressEvent {
  sku_index?: number;
  sku_total?: number;
  sku_id?: string;
  status: string;
}

export const UNAVAILABLE = "unavailable_rate_limited";
