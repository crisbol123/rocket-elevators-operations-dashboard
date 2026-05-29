from __future__ import annotations
import asyncio
import math
import os
from pathlib import Path

from datetime import date

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

GO_API = f"http://localhost:{os.getenv('GO_API_PORT', '8081')}"

BASE = Path(__file__).parent
PAGE_SIZE = 10

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE / "templates"))



@app.middleware("http")
async def dev_delay(request: Request, call_next):
    await asyncio.sleep(0.2)
    return await call_next(request)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            all_r, active_r, expired_r = await asyncio.gather(
                client.get(f"{GO_API}/api/elevators", params={"page": 1}),
                client.get(f"{GO_API}/api/elevators", params={"status": "ACTIVE", "page": 1}),
                client.get(f"{GO_API}/api/elevators", params={"expired": "yes", "page": 1}),
            )
    except httpx.ConnectError:
        return templates.TemplateResponse(
            request=request, name="api_error.html",
            context={"message": f"Go API is unavailable. Start the server on {GO_API}."},
            status_code=503,
        )

    total = all_r.json().get("total", 0) if all_r.status_code == 200 else 0
    active = active_r.json().get("total", 0) if active_r.status_code == 200 else 0
    expired = expired_r.json().get("total", 0) if expired_r.status_code == 200 else 0

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"total": f"{total:,}", "active": f"{active:,}", "expired": f"{expired:,}"},
    )


@app.get("/fragments/table", response_class=HTMLResponse)
async def table_fragment(
    request: Request,
    page: int = Query(default=1, ge=1),
    status: str = Query(default="all"),
    expired: str = Query(default="all"),
    inspection: str = Query(default="all"),
    search_id: str = Query(default=""),
    search_location: str = Query(default=""),
    sort_by: str = Query(default="elevator_id"),
    sort_dir: str = Query(default="asc"),
) -> HTMLResponse:
    params = {
        "page": page, "status": status, "expired": expired,
        "inspection": inspection, "search_id": search_id,
        "search_location": search_location, "sort_by": sort_by, "sort_dir": sort_dir,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{GO_API}/api/elevators", params=params)
    except httpx.ConnectError:
        return templates.TemplateResponse(
            request=request, name="api_error.html",
            context={"message": f"Go API is unavailable. Start the server on {GO_API}."},
            status_code=503,
        )

    data = r.json()
    today = date.today().isoformat()

    rows = []
    for item in data["data"]:
        expiry = item["license_expiry_date"]
        rows.append({
            "elevator_id": item["elevator_id"],
            "location": item["location"],
            "city": item["city"],
            "license_status": item["license_status"],
            "license_expiry_date_fmt": expiry,
            "is_expired": bool(expiry) and expiry < today,
            "is_overdue": item["is_overdue"],
            "risk_level": item.get("risk_level", ""),
        })

    total = data["total"]
    actual_page = data["page"]
    total_pages = data["total_pages"]
    start = (actual_page - 1) * PAGE_SIZE + 1 if total > 0 else 0
    end = min(actual_page * PAGE_SIZE, total)

    return templates.TemplateResponse(
        request=request,
        name="table_fragment.html",
        context={
            "rows": rows,
            "page": actual_page,
            "total_pages": total_pages,
            "start": f"{start:,}" if total > 0 else "0",
            "end": f"{end:,}",
            "total": f"{total:,}",
            "status": status,
            "expired": expired,
            "inspection": inspection,
            "search_id": search_id,
            "search_location": search_location,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
            "card_total": f"{total:,}",
        },
    )


@app.get("/elevator/{elevator_id}", response_class=HTMLResponse)
async def elevator_detail(request: Request, elevator_id: int) -> HTMLResponse:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            detail_r, insp_r = await asyncio.gather(
                client.get(f"{GO_API}/api/elevators/{elevator_id}"),
                client.get(f"{GO_API}/api/elevators/{elevator_id}/inspections"),
            )
    except httpx.ConnectError:
        return templates.TemplateResponse(
            request=request,
            name="api_error.html",
            context={"message": f"Go API is unavailable. Start the server on {GO_API}."},
            status_code=503,
        )

    if detail_r.status_code == 404:
        raise HTTPException(status_code=404, detail="Elevator not found")

    detail = detail_r.json()
    inspections = [
        {"date": i["date"], "type": i["type"], "outcome": i["outcome"]}
        for i in insp_r.json()
    ]

    return templates.TemplateResponse(
        request=request,
        name="elevator_detail.html",
        context={
            "elevator_id": detail["elevator_id"],
            "device_type": detail["device_type"],
            "device_status": detail["device_status"],
            "license_number": detail["license_number"],
            "license_status": detail["license_status"],
            "license_expiry_date": detail["license_expiry_date"],
            "location": detail["location"],
            "inspections": inspections,
            "alteration_count": detail["alteration_count"],
            "incident_count": detail["incident_count"],
            "is_overdue": detail["is_overdue"],
        },
    )


@app.get("/elevator/{elevator_id}/risk", response_class=HTMLResponse)
async def elevator_risk(request: Request, elevator_id: int) -> HTMLResponse:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{GO_API}/api/elevators/{elevator_id}/risk")
    except httpx.ConnectError:
        return HTMLResponse(content='<p class="text-sm text-slate-400">Risk API unavailable.</p>', status_code=503)

    if r.status_code == 503:
        return HTMLResponse(content='<p class="text-sm text-slate-400">Risk scores not yet available.</p>')
    if r.status_code == 404:
        return HTMLResponse(content='<p class="text-sm text-slate-400">No risk prediction for this elevator.</p>')

    risk = r.json()
    level_class = {
        "low": "bg-emerald-100 text-emerald-700",
        "medium": "bg-amber-100 text-amber-700",
        "high": "bg-red-100 text-red-700",
    }.get(risk["risk_level"], "bg-slate-100 text-slate-600")

    return HTMLResponse(content=f"""
        <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {level_class}">
            {risk["risk_level"].upper()} — {risk["risk_score"]:.2f}
        </span>
        <p class="text-xs text-slate-400 mt-1">As of {risk["predicted_at"]}</p>
    """)


@app.get("/fragments/fleet-health", response_class=HTMLResponse)
async def fleet_health(request: Request) -> HTMLResponse:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{GO_API}/api/fleet/stats")
    except httpx.ConnectError:
        return HTMLResponse(content='<p class="text-sm text-red-500">Fleet stats unavailable — Go API is not running.</p>')

    if r.status_code == 503:
        return HTMLResponse(content='<p class="text-sm text-slate-400">Fleet stats not available — predictions have not been generated yet.</p>')

    stats = r.json()
    by_risk = stats["by_risk_level"]
    total = stats["total_elevators"]
    pass_rate = round(stats["inspection_pass_rate"] * 100, 1)

    return templates.TemplateResponse(
        request=request,
        name="fleet_health.html",
        context={
            "total_elevators": f"{total:,}",
            "high": f"{by_risk.get('high', 0):,}",
            "medium": f"{by_risk.get('medium', 0):,}",
            "low": f"{by_risk.get('low', 0):,}",
            "pass_rate": f"{pass_rate}%",
        },
    )


@app.get("/alerts", response_class=HTMLResponse)
async def alerts_page(request: Request, page: int = Query(default=1, ge=1)) -> HTMLResponse:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{GO_API}/api/fleet/alerts")
    except httpx.ConnectError:
        return templates.TemplateResponse(
            request=request, name="api_error.html",
            context={"message": f"Go API is unavailable. Start the server on {GO_API}."},
            status_code=503,
        )

    if r.status_code == 503:
        return templates.TemplateResponse(
            request=request, name="api_error.html",
            context={"message": "Predictions not available — run the prediction notebook first."},
            status_code=503,
        )

    all_alerts = r.json()
    total = len(all_alerts)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    return templates.TemplateResponse(
        request=request,
        name="alerts.html",
        context={
            "alerts": all_alerts[start:end],
            "page": page,
            "total_pages": total_pages,
            "total": f"{total:,}",
            "start": f"{start + 1:,}" if total > 0 else "0",
            "end": f"{end:,}",
        },
    )


@app.get("/fragments/close", response_class=HTMLResponse)
def close_panel() -> HTMLResponse:
    return HTMLResponse(content="")
