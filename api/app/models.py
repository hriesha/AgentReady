"""ORM models: an audit run and its per-SKU results.

The parsed catalog and every result are stored as JSON so a partial run
is still useful and the API can serve results without recomputation.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

RUN_PENDING = "pending"
RUN_RUNNING = "running"
RUN_COMPLETE = "complete"
RUN_FAILED = "failed"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(16), default=RUN_PENDING)
    sku_count: Mapped[int] = mapped_column(Integer, default=0)
    mapping_report: Mapped[dict] = mapped_column(JSON, default=dict)
    catalog: Mapped[list] = mapped_column(JSON, default=list)
    aggregates: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SkuResult(Base):
    __tablename__ = "sku_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("audit_runs.id"), index=True
    )
    sku_id: Mapped[str] = mapped_column(String(64), index=True)
    result: Mapped[dict] = mapped_column(JSON)
