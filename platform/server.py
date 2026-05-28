from __future__ import annotations
import asyncio
import math
import os
from pathlib import Path

import httpx
import pandas as pd
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

GO_API = f"http://localhost:{os.getenv('GO_API_PORT', '8081')}"

BASE = Path(__file__).parent
DATA = BASE.parent / "data"
PAGE_SIZE = 10

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE / "templates"))


# DEV ONLY — remove before deploying to production.
# Requests are near-instant locally so the loading spinner is invisible without this delay.
@app.middleware("http")
async def dev_delay(request: Request, call_next):
    await asyncio.sleep(0.2)
    return await call_next(request)

DF: pd.DataFrame = pd.DataFrame()
EXPIRY: pd.Series = pd.Series(dtype="datetime64[ns]")
INSTALLED: pd.DataFrame = pd.DataFrame()
INSPECTIONS: pd.DataFrame = pd.DataFrame()
ALTERED: pd.DataFrame = pd.DataFrame()
INCIDENTS: pd.DataFrame = pd.DataFrame()
OVERDUE_IDS: set[int] = set()


@app.on_event("startup")
def load_data() -> None:
    global DF, EXPIRY, INSTALLED, INSPECTIONS, ALTERED, INCIDENTS, OVERDUE_IDS
    DF = pd.read_csv(BASE / "elevator_fleet.csv").sort_values("elevator_id").reset_index(drop=True)
    EXPIRY = pd.to_datetime(DF["license_expiry_date"], format="%d-%b-%y", errors="coerce")
    INSTALLED = pd.read_json(DATA / "installed.json")
    INSPECTIONS = pd.read_csv(DATA / "inspection.csv")
    INSPECTIONS["_date"] = pd.to_datetime(INSPECTIONS["Latest_INSPECTION_Date"], format="%m/%d/%Y", errors="coerce")
    ALTERED = pd.read_json(DATA / "altered.json")
    INCIDENTS = pd.read_json(DATA / "incident.json")
    last_insp = INSPECTIONS.groupby("ElevatingDevicesNumber")["_date"].max()
    ref_date = pd.Timestamp.today().normalize()
    OVERDUE_IDS = set(last_insp[last_insp < (ref_date - pd.Timedelta(days=365))].index)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    today = pd.Timestamp.today().normalize()
    total = len(DF)
    active = int((DF["license_status"] == "ACTIVE").sum())
    expired = int((EXPIRY < today).sum())
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"total": f"{total:,}", "active": f"{active:,}", "expired": f"{expired:,}"},
    )


@app.get("/fragments/table", response_class=HTMLResponse)
def table_fragment(
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
    today = pd.Timestamp.today().normalize()

    df = DF.copy()
    df["_expiry"] = EXPIRY.values

    if status != "all":
        df = df[df["license_status"] == status]

    if expired == "yes":
        df = df[df["_expiry"] < today]
    elif expired == "no":
        df = df[~(df["_expiry"] < today)]

    if inspection == "overdue":
        df = df[df["elevator_id"].isin(OVERDUE_IDS)]
    elif inspection == "ok":
        df = df[~df["elevator_id"].isin(OVERDUE_IDS)]

    if search_id:
        df = df[df["elevator_id"].astype(str).str.startswith(search_id.strip()[:100])]
    if search_location:
        df = df[df["location"].str.lower().str.contains(search_location.strip()[:100].lower(), na=False)]

    if sort_by == "license_expiry_date":
        df = df.sort_values("_expiry", ascending=(sort_dir == "asc"), na_position="last")
    else:
        df = df.sort_values("elevator_id", ascending=(sort_dir == "asc"))

    df = df.reset_index(drop=True)

    total = len(df)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    card_total = f"{total:,}"
    card_active = f"{int((df['license_status'] == 'ACTIVE').sum()):,}"
    card_expired = f"{int((df['_expiry'] < today).sum()):,}"

    rows = []
    for _, row in df.iloc[start:end].iterrows():
        exp_dt = row["_expiry"]
        rows.append({
            "elevator_id": int(row["elevator_id"]) if pd.notna(row["elevator_id"]) else "",
            "location": "" if pd.isna(row["location"]) else str(row["location"]),
            "city": "" if pd.isna(row["city"]) else str(row["city"]),
            "license_status": "" if pd.isna(row["license_status"]) else str(row["license_status"]),
            "license_expiry_date_fmt": exp_dt.strftime("%Y-%m-%d") if pd.notna(exp_dt) else "",
            "is_expired": pd.notna(exp_dt) and exp_dt < today,
            "is_overdue": int(row["elevator_id"]) in OVERDUE_IDS,
        })

    return templates.TemplateResponse(
        request=request,
        name="table_fragment.html",
        context={
            "rows": rows,
            "page": page,
            "total_pages": total_pages,
            "start": f"{start + 1:,}" if total > 0 else "0",
            "end": f"{end:,}",
            "total": f"{total:,}",
            "status": status,
            "expired": expired,
            "inspection": inspection,
            "search_id": search_id,
            "search_location": search_location,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
            "card_total": card_total,
            "card_active": card_active,
            "card_expired": card_expired,
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


@app.get("/fragments/close", response_class=HTMLResponse)
def close_panel() -> HTMLResponse:
    return HTMLResponse(content="")
