"""FastAPI app: catalog upload, audit runs, results, and SSE progress.

Audits run in a background task after start returns, and every SKU result
is persisted as it completes, so a partial run is still useful. Progress
streams over SSE from the in-memory broker.
"""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import select

from app import models
from app.catalog.ingest import CatalogValidationError, ingest_catalog
from app.config import get_settings
from app.db import create_session, init_db
from app.export.csv_export import audit_report_csv, rewritten_catalog_csv
from app.llm.provider import get_provider
from app.progress import ProgressBroker
from app.schemas import (
    RunResultsResponse,
    SkuResultModel,
    StartResponse,
    UploadResponse,
)
from app.scoring.pipeline import run_audit

logger = logging.getLogger("app.api")

SAMPLE_CATALOG_PATH = Path(__file__).resolve().parents[1] / "tests" / "sample_catalog.csv"

broker = ProgressBroker()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AgentReady API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_run(run_id: str) -> models.AuditRun:
    with create_session() as session:
        run = session.get(models.AuditRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="audit run not found")
    return run


@app.post("/api/catalog/upload", response_model=UploadResponse)
async def upload_catalog(file: UploadFile) -> UploadResponse:
    try:
        ingested = ingest_catalog(file.file)
    except CatalogValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(error),
                "missing_required": error.missing_required,
            },
        ) from error
    mapping_report = {
        "mapped": ingested.mapping_report.mapped,
        "extra": list(ingested.mapping_report.extra),
    }
    run = models.AuditRun(
        id=uuid.uuid4().hex,
        status=models.RUN_PENDING,
        sku_count=ingested.sku_count,
        mapping_report=mapping_report,
        catalog=ingested.skus,
    )
    with create_session() as session:
        session.add(run)
        session.commit()
    return UploadResponse(
        run_id=run.id, sku_count=run.sku_count, mapping_report=mapping_report
    )


@app.get("/api/sample-catalog")
async def sample_catalog() -> FileResponse:
    return FileResponse(
        SAMPLE_CATALOG_PATH, media_type="text/csv", filename="sample_catalog.csv"
    )


@app.post("/api/audit/{run_id}/start", response_model=StartResponse)
async def start_audit(run_id: str, background_tasks: BackgroundTasks) -> StartResponse:
    with create_session() as session:
        run = session.get(models.AuditRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="audit run not found")
        if run.status != models.RUN_PENDING:
            raise HTTPException(
                status_code=409, detail=f"audit run is already {run.status}"
            )
        run.status = models.RUN_RUNNING
        session.commit()
    broker.start(run_id)
    background_tasks.add_task(execute_audit, run_id)
    return StartResponse(run_id=run_id, status=models.RUN_RUNNING)


def execute_audit(run_id: str) -> None:
    """Run the pipeline for a stored catalog, persisting each SKU result
    as it completes and publishing progress to the broker."""
    with create_session() as session:
        run = session.get(models.AuditRun, run_id)
        skus = run.catalog if run is not None else []

    def persist(result: dict) -> None:
        with create_session() as session:
            session.add(
                models.SkuResult(
                    run_id=run_id, sku_id=result["sku_id"], result=result
                )
            )
            session.commit()

    def on_progress(index: int, total: int, sku_id: str, status: str) -> None:
        broker.publish(
            run_id,
            {"sku_index": index, "sku_total": total, "sku_id": sku_id, "status": status},
        )

    try:
        outcome = run_audit(
            skus, provider=get_provider(), on_progress=on_progress, persist=persist
        )
    except Exception:
        logger.exception("audit run %s failed", run_id)
        with create_session() as session:
            run = session.get(models.AuditRun, run_id)
            if run is not None:
                run.status = models.RUN_FAILED
                session.commit()
        broker.publish(run_id, {"status": models.RUN_FAILED}, final=True)
        return

    with create_session() as session:
        run = session.get(models.AuditRun, run_id)
        if run is not None:
            run.aggregates = outcome["aggregates"]
            run.status = models.RUN_COMPLETE
            session.commit()
    broker.publish(
        run_id,
        {"status": models.RUN_COMPLETE, "sku_total": len(skus)},
        final=True,
    )


@app.get("/api/audit/{run_id}/stream")
async def stream_progress(run_id: str) -> StreamingResponse:
    run = _load_run(run_id)
    run_status = run.status

    def event_stream():
        streamed_any = False
        for event in broker.subscribe(run_id):
            streamed_any = True
            if event["final"]:
                yield f"event: done\ndata: {json.dumps(event['data'])}\n\n"
            else:
                yield f"data: {json.dumps(event['data'])}\n\n"
        if not streamed_any:
            yield f"event: done\ndata: {json.dumps({'status': run_status})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


def _load_results(run_id: str) -> tuple[models.AuditRun, list[dict]]:
    with create_session() as session:
        run = session.get(models.AuditRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="audit run not found")
        rows = (
            session.execute(
                select(models.SkuResult)
                .where(models.SkuResult.run_id == run_id)
                .order_by(models.SkuResult.id)
            )
            .scalars()
            .all()
        )
    return run, [row.result for row in rows]


def _csv_download(content: str, filename: str) -> Response:
    return Response(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/audit/{run_id}/export/audit.csv")
async def export_audit_report(run_id: str) -> Response:
    _run, results = _load_results(run_id)
    return _csv_download(audit_report_csv(results), "agentready_audit.csv")


@app.get("/api/audit/{run_id}/export/rewritten.csv")
async def export_rewritten_catalog(run_id: str) -> Response:
    run, results = _load_results(run_id)
    return _csv_download(
        rewritten_catalog_csv(run.catalog or [], results),
        "agentready_rewritten_catalog.csv",
    )


@app.get("/api/audit/{run_id}", response_model=RunResultsResponse)
async def get_results(run_id: str) -> RunResultsResponse:
    run, results = _load_results(run_id)
    return RunResultsResponse(
        run_id=run.id,
        status=run.status,
        sku_count=run.sku_count,
        mapping_report=run.mapping_report,
        aggregates=run.aggregates,
        sku_results=results,
    )


@app.get("/api/audit/{run_id}/sku/{sku_id}", response_model=SkuResultModel)
async def get_sku_result(run_id: str, sku_id: str) -> SkuResultModel:
    _load_run(run_id)
    with create_session() as session:
        row = (
            session.execute(
                select(models.SkuResult)
                .where(
                    models.SkuResult.run_id == run_id,
                    models.SkuResult.sku_id == sku_id,
                )
                .order_by(models.SkuResult.id)
            )
            .scalars()
            .first()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="SKU result not found")
    return row.result
