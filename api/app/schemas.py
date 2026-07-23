"""Typed request and response models for the API. These mirror the
JSON-ready dicts produced by the pipeline so responses stay validated."""

from typing import Any

from pydantic import BaseModel


class MappingReportModel(BaseModel):
    mapped: dict[str, str]
    extra: list[str]


class UploadResponse(BaseModel):
    run_id: str
    sku_count: int
    mapping_report: MappingReportModel


class StartResponse(BaseModel):
    run_id: str
    status: str


class AttributeScoreModel(BaseModel):
    name: str
    weight: int
    status: str
    score: float
    reason: str


class CompletenessModel(BaseModel):
    score: float
    attributes: list[AttributeScoreModel]
    missing: list[str]
    vague: list[str]


class QueryModel(BaseModel):
    query: str
    intent_type: str
    would_surface: bool
    confidence: float
    missing_info: list[str]
    reason: str


class SimulationModel(BaseModel):
    status: str
    surface_rate: float | None = None
    queries: list[QueryModel]


class GapModel(BaseModel):
    attribute: str
    status: str
    weight: int
    frequency_in_failed_queries: int
    impact: float
    reason: str
    agent_need: str


class RewriteOutcomeModel(BaseModel):
    attribute: str
    original: Any = None
    value: Any = None
    needs_human: str | None = None


class RewriteModel(BaseModel):
    status: str
    outcomes: list[RewriteOutcomeModel]


class SkuResultModel(BaseModel):
    sku_id: str
    title: str | None = None
    revenue_at_risk: float
    revenue_is_estimate: bool
    readiness: float
    before_score: float
    after_score: float | None = None
    completeness: CompletenessModel
    simulation: SimulationModel
    gaps: list[GapModel]
    rewrite: RewriteModel


class CatalogGapModel(BaseModel):
    attribute: str
    sku_count: int
    share: float
    total_impact: float


class AggregatesModel(BaseModel):
    sku_count: int
    readiness_revenue_weighted: float
    readiness_unweighted: float
    revenue_at_risk_total: float
    rate_limited_skus: int
    top_gaps: list[CatalogGapModel]


class RunResultsResponse(BaseModel):
    run_id: str
    status: str
    sku_count: int
    mapping_report: MappingReportModel
    aggregates: AggregatesModel | None = None
    sku_results: list[SkuResultModel]
