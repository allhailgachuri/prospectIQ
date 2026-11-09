"""
ProspectIQ FastAPI backend.

Run:
    .venv/Scripts/uvicorn api.main:app --reload --port 8000
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3
from pathlib import Path
import math

from prospectiq.storage import (
    connect, initialize_database, get_stats, export_csv,
    get_qualified_prospects, get_businesses_for_website_check,
)
from prospectiq.intelligence import analyse_business
from prospectiq.outreach import build_outreach_package
from prospectiq.logger import configure_logging
from prospectiq.excel_export import generate_excel

configure_logging()
initialize_database()

# Ensure CRM columns exist from the start
def _ensure_crm_columns():
    """Add CRM columns if not present."""
    needed = {"crm_status": "TEXT", "crm_notes": "TEXT", "crm_follow_up": "TEXT"}
    with connect() as conn:
        existing = {r[1] for r in conn.execute("PRAGMA table_info(businesses)").fetchall()}
        for col, typ in needed.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE businesses ADD COLUMN {col} {typ}")

_ensure_crm_columns()

app = FastAPI(
    title="ProspectIQ API",
    description="Nairobi Business Discovery & Client Acquisition Intelligence",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:6060,http://localhost:5173,http://localhost:3000"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row) -> dict:
    if row is None:
        return {}
    return dict(row)


def _get_db_conn():
    return connect()


# ---------------------------------------------------------------------------
# Stats & Overview
# ---------------------------------------------------------------------------

@app.get("/api/stats")
def api_stats():
    """Dashboard summary statistics."""
    stats = get_stats()

    with connect() as conn:
        website_statuses = conn.execute(
            "SELECT website_status, COUNT(*) as n FROM businesses "
            "WHERE website_status IS NOT NULL GROUP BY website_status ORDER BY n DESC"
        ).fetchall()
        audit_labels = conn.execute(
            "SELECT audit_quality_label, COUNT(*) as n FROM businesses "
            "WHERE audit_quality_label IS NOT NULL GROUP BY audit_quality_label ORDER BY n DESC"
        ).fetchall()
        crm_statuses = conn.execute(
            "SELECT crm_status, COUNT(*) as n FROM businesses "
            "WHERE crm_status IS NOT NULL GROUP BY crm_status ORDER BY n DESC"
        ).fetchall()
        total_checked = conn.execute(
            "SELECT COUNT(*) FROM businesses WHERE website_status IS NOT NULL"
        ).fetchone()[0]

    return {
        **stats,
        "total_checked": total_checked,
        "website_statuses": [dict(r) for r in website_statuses],
        "audit_labels": [dict(r) for r in audit_labels],
        "crm_statuses": [dict(r) for r in crm_statuses],
    }


# ---------------------------------------------------------------------------
# Businesses list (with filtering + search + pagination)
# ---------------------------------------------------------------------------

@app.get("/api/businesses")
def api_businesses(
    search:       Optional[str] = Query(None),
    category:     Optional[str] = Query(None),
    neighbourhood:Optional[str] = Query(None),
    website_status:Optional[str] = Query(None),
    audit_label:  Optional[str] = Query(None),
    priority:     Optional[str] = Query(None),
    has_phone:    Optional[bool] = Query(None),
    has_email:    Optional[bool] = Query(None),
    has_website:  Optional[bool] = Query(None),
    crm_status:   Optional[str] = Query(None),
    page:         int = Query(1, ge=1),
    page_size:    int = Query(25, ge=1, le=100),
):
    """
    Paginated, filterable business list.
    Returns { items, total, page, page_size, pages }.
    """
    where_clauses = []
    params = []

    if search:
        where_clauses.append("(name LIKE ? OR description LIKE ? OR address LIKE ?)")
        like = f"%{search}%"
        params += [like, like, like]
    if category:
        where_clauses.append("category = ?")
        params.append(category)
    if neighbourhood:
        where_clauses.append("neighbourhood LIKE ?")
        params.append(f"%{neighbourhood}%")
    if website_status:
        where_clauses.append("website_status = ?")
        params.append(website_status)
    if audit_label:
        where_clauses.append("audit_quality_label = ?")
        params.append(audit_label)
    if has_phone is not None:
        where_clauses.append("phone IS " + ("NOT NULL" if has_phone else "NULL"))
    if has_email is not None:
        where_clauses.append("email IS " + ("NOT NULL" if has_email else "NULL"))
    if has_website is not None:
        where_clauses.append("website IS " + ("NOT NULL" if has_website else "NULL"))
    if crm_status:
        where_clauses.append("crm_status = ?")
        params.append(crm_status)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    offset = (page - 1) * page_size

    with connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM businesses {where_sql}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"SELECT * FROM businesses {where_sql} "
            f"ORDER BY name COLLATE NOCASE "
            f"LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    items = [_row_to_dict(r) for r in rows]
    # Attach intelligence score for each
    for item in items:
        intel = analyse_business(item)
        item["lead_score"] = intel["lead_score"]
        item["priority"]   = intel["priority"]
        item["industry"]   = intel["industry"]

    return {
        "items":     items,
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     max(1, (total + page_size - 1) // page_size),
    }


# ---------------------------------------------------------------------------
# Single business + full profile
# ---------------------------------------------------------------------------

@app.get("/api/businesses/{source_record_id:path}")
def api_business_detail(source_record_id: str):
    """Full business profile with intelligence + outreach package."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM businesses WHERE source_record_id = ?",
            (source_record_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Business not found")

    biz      = _row_to_dict(row)
    intel    = analyse_business(biz)
    outreach = build_outreach_package(biz, intel)

    return {
        "business":    biz,
        "intelligence": intel,
        "outreach":    outreach,
    }


# ---------------------------------------------------------------------------
# CRM actions
# ---------------------------------------------------------------------------

class CRMUpdate(BaseModel):
    crm_status:    Optional[str] = None   # new, contacted, interested, not_interested, dnc
    crm_notes:     Optional[str] = None
    crm_follow_up: Optional[str] = None   # ISO date string


@app.patch("/api/businesses/{source_record_id:path}/crm")
def api_crm_update(source_record_id: str, update: CRMUpdate):
    """Update CRM status, notes and follow-up date for a prospect."""
    fields, values = [], []
    if update.crm_status is not None:
        fields.append("crm_status = ?")
        values.append(update.crm_status)
    if update.crm_notes is not None:
        fields.append("crm_notes = ?")
        values.append(update.crm_notes)
    if update.crm_follow_up is not None:
        fields.append("crm_follow_up = ?")
        values.append(update.crm_follow_up)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(source_record_id)
    with connect() as conn:
        conn.execute(
            f"UPDATE businesses SET {', '.join(fields)} WHERE source_record_id = ?",
            values,
        )

    return {"ok": True}


# ---------------------------------------------------------------------------
# Filter options (for dropdowns)
# ---------------------------------------------------------------------------

@app.get("/api/filters")
def api_filters():
    """Return all distinct values for filter dropdowns."""
    with connect() as conn:
        cats = [r[0] for r in conn.execute(
            "SELECT DISTINCT category FROM businesses WHERE category IS NOT NULL ORDER BY category"
        ).fetchall()]
        nbs = [r[0] for r in conn.execute(
            "SELECT DISTINCT neighbourhood FROM businesses "
            "WHERE neighbourhood IS NOT NULL ORDER BY neighbourhood"
        ).fetchall()]
        ws = [r[0] for r in conn.execute(
            "SELECT DISTINCT website_status FROM businesses "
            "WHERE website_status IS NOT NULL ORDER BY website_status"
        ).fetchall()]
        ql = [r[0] for r in conn.execute(
            "SELECT DISTINCT audit_quality_label FROM businesses "
            "WHERE audit_quality_label IS NOT NULL ORDER BY audit_quality_label"
        ).fetchall()]

    return {
        "categories":       cats,
        "neighbourhoods":   nbs,
        "website_statuses": ws,
        "audit_labels":     ql,
        "priorities":       ["HIGH", "MEDIUM", "LOW", "NEEDS_MANUAL_REVIEW"],
        "crm_statuses":     ["new", "contacted", "interested", "not_interested", "dnc"],
    }


# ---------------------------------------------------------------------------
# Background jobs
# ---------------------------------------------------------------------------

_job_status: dict[str, dict] = {}


def _run_discovery_job(job_id: str, bbox: tuple[float, float, float, float]):
    from prospectiq.normalize import normalize_element
    from prospectiq.overpass import fetch_business_elements
    from prospectiq.storage import upsert_many

    _job_status[job_id] = {"status": "running", "done": 0, "total": 1, "error": None}
    try:
        elements = fetch_business_elements(bbox)
        records = [record for element in elements if (record := normalize_element(element))]
        saved = upsert_many(records)
        _job_status[job_id].update({"status": "done", "done": 1, "total": 1, "records": saved})
    except Exception as exc:
        _job_status[job_id].update({"status": "error", "error": str(exc)})


@app.post("/api/jobs/discover")
def api_start_discovery(background_tasks: BackgroundTasks, bbox: str = Query(...)):
    """Discover businesses in one bounded south,west,north,east coordinate box."""
    try:
        bounds = tuple(float(part.strip()) for part in bbox.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox must contain four decimal coordinates") from exc
    if len(bounds) != 4 or not all(math.isfinite(value) for value in bounds):
        raise HTTPException(status_code=422, detail="bbox must contain four finite decimal coordinates")
    south, west, north, east = bounds
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise HTTPException(status_code=422, detail="bbox coordinates are out of range or reversed")
    if north - south > 0.5 or east - west > 0.5 or (north - south) * (east - west) > 0.15:
        raise HTTPException(
            status_code=422,
            detail="Choose a smaller area: bbox dimensions are limited to 0.5 degrees and total area to 0.15 square degrees",
        )

    import uuid
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_discovery_job, job_id, bounds)
    return {"job_id": job_id}


def _run_check_job(job_id: str, limit: int):
    from prospectiq.website import check_business_website
    from prospectiq.storage import update_website_check
    _job_status[job_id] = {"status": "running", "done": 0, "total": 0, "error": None}
    try:
        businesses = get_businesses_for_website_check(limit=limit)
        _job_status[job_id]["total"] = len(businesses)
        for biz in businesses:
            result = check_business_website(biz)
            update_website_check(result)
            _job_status[job_id]["done"] += 1
        _job_status[job_id]["status"] = "done"
    except Exception as exc:
        _job_status[job_id]["status"] = "error"
        _job_status[job_id]["error"] = str(exc)


def _run_report_job(job_id: str, limit: int):
    from prospectiq.intelligence import analyse_business
    from prospectiq.outreach import build_outreach_package
    from prospectiq.report import generate_report
    _job_status[job_id] = {"status": "running", "done": 0, "total": 0, "file": None, "error": None}
    try:
        prospects_raw = get_qualified_prospects(limit=limit)
        _job_status[job_id]["total"] = len(prospects_raw)
        prospects = []
        for biz in prospects_raw:
            intel    = analyse_business(biz)
            outreach = build_outreach_package(biz, intel)
            prospects.append({"business": biz, "intelligence": intel, "outreach": outreach})
            _job_status[job_id]["done"] += 1
        prospects.sort(key=lambda p: p["intelligence"].get("lead_score", 0), reverse=True)
        db_stats = get_stats()
        report_stats = {
            "total_discovered": db_stats["total"], "total_unique": db_stats["total"],
            "with_email": db_stats["with_email"], "with_phone": db_stats["with_phone"],
            "by_category": db_stats["by_category"], "by_neighbourhood": db_stats["by_neighbourhood"],
            "qualified": len(prospects),
            "high_priority":  sum(1 for p in prospects if p["intelligence"]["priority"] == "HIGH"),
            "medium_priority":sum(1 for p in prospects if p["intelligence"]["priority"] == "MEDIUM"),
            "needs_review":   sum(1 for p in prospects if p["intelligence"]["priority"] == "NEEDS_MANUAL_REVIEW"),
            "verified_websites": sum(1 for p in prospects if p["business"].get("website_status") == "VERIFIED_WEBSITE"),
            "no_website":     sum(1 for p in prospects if p["business"].get("website_presence") == "not_listed_in_osm"),
            "unreachable":    sum(1 for p in prospects if p["business"].get("website_status") == "WEBSITE_UNREACHABLE"),
            "weak_website":   sum(1 for p in prospects if p["business"].get("audit_quality_label") in ("POOR", "WEAK")),
        }
        path = generate_report(prospects, report_stats, output_dir="reports")
        excel_path = generate_excel(prospects, output_dir="reports")
        _job_status[job_id]["status"] = "done"
        _job_status[job_id]["file"]   = str(path)
        _job_status[job_id]["files"]  = [str(path), str(excel_path)]
    except Exception as exc:
        _job_status[job_id]["status"] = "error"
        _job_status[job_id]["error"]  = str(exc)


@app.post("/api/jobs/check")
def api_start_check(background_tasks: BackgroundTasks, limit: int = Query(100, ge=1, le=500)):
    """Start a background website-check job."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_check_job, job_id, limit)
    return {"job_id": job_id}


@app.post("/api/jobs/report")
def api_start_report(background_tasks: BackgroundTasks, limit: int = Query(50, ge=1, le=200)):
    """Start a background report-generation job."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_report_job, job_id, limit)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str):
    """Poll a background job's status."""
    if job_id not in _job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_status[job_id]


@app.get("/api/reports/latest")
def api_latest_report():
    """Download the most recently generated Word report."""
    reports_dir = Path("reports")
    files = sorted(reports_dir.glob("*.docx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No reports generated yet")
    return FileResponse(
        path=str(files[0]),
        filename=files[0].name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/api/reports/latest/excel")
def api_latest_excel_report():
    """Download the most recently generated outreach workbook."""
    reports_dir = Path("reports")
    files = sorted(reports_dir.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No Excel reports generated yet")
    return FileResponse(
        path=str(files[0]),
        filename=files[0].name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/reports/file/{filename}")
def api_download_report(filename: str):
    """Download a generated report by filename, constrained to the reports directory."""
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".docx", ".xlsx"}:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path("reports") / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if path.suffix.lower() == ".docx"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(path=str(path), filename=path.name, media_type=media_type)


@app.get("/api/reports")
def api_list_reports():
    """List all generated reports."""
    reports_dir = Path("reports")
    if not reports_dir.exists():
        return []
    files = sorted(
        [*reports_dir.glob("*.docx"), *reports_dir.glob("*.xlsx")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return [
        {
            "name": f.name,
            "size_kb": round(f.stat().st_size / 1024, 1),
            "created": f.stat().st_mtime,
        }
        for f in files
    ]


@app.get("/api/export/csv")
def api_export_csv():
    """Export all businesses to CSV and return the file."""
    path = "exports/businesses.csv"
    export_csv(path)
    return FileResponse(
        path=path,
        filename="ProspectIQ_Nairobi_Businesses.csv",
        media_type="text/csv",
    )


@app.get("/api/export/xlsx")
def api_export_xlsx():
    """Export qualified prospects as the compact six-column outreach workbook."""
    prospects = []
    for business in get_qualified_prospects(limit=2000):
        intelligence = analyse_business(business)
        prospects.append({"business": business, "intelligence": intelligence})
    path = generate_excel(prospects, output_dir="exports")
    return FileResponse(
        path=str(path),
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
