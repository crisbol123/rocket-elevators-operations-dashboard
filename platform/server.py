from __future__ import annotations
import asyncio
import math
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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
def elevator_detail(request: Request, elevator_id: int) -> HTMLResponse:
    fleet_row = DF[DF["elevator_id"] == elevator_id]
    if fleet_row.empty:
        raise HTTPException(status_code=404, detail="Elevator not found")

    fleet = fleet_row.iloc[0]
    exp_dt = pd.to_datetime(fleet["license_expiry_date"], format="%d-%b-%y", errors="coerce")

    installed_row = INSTALLED[INSTALLED["Elevating devices number"] == elevator_id]
    device_type = str(installed_row.iloc[0]["Device Type"]) if not installed_row.empty else ""
    device_status = str(installed_row.iloc[0]["DeviceStatus"]) if not installed_row.empty else ""

    insp_df = INSPECTIONS[INSPECTIONS["ElevatingDevicesNumber"] == elevator_id].sort_values("_date", ascending=False)
    inspections = [
        {
            "date": row["_date"].strftime("%Y-%m-%d") if pd.notna(row["_date"]) else "",
            "type": str(row["InspectionType"]),
            "outcome": str(row["InspectionOutcome"]),
        }
        for _, row in insp_df.iterrows()
    ]

    alteration_count = int((ALTERED["Elevating Devices Number"] == elevator_id).sum())
    incident_count = int((INCIDENTS["elevating devices number"] == elevator_id).sum())

    return templates.TemplateResponse(
        request=request,
        name="elevator_detail.html",
        context={
            "elevator_id": elevator_id,
            "device_type": device_type,
            "device_status": device_status,
            "license_number": "" if pd.isna(fleet["license_number"]) else str(fleet["license_number"]),
            "license_status": "" if pd.isna(fleet["license_status"]) else str(fleet["license_status"]),
            "license_expiry_date": exp_dt.strftime("%Y-%m-%d") if pd.notna(exp_dt) else "",
            "location": "" if pd.isna(fleet["location"]) else str(fleet["location"]),
            "inspections": inspections,
            "alteration_count": alteration_count,
            "incident_count": incident_count,
            "is_overdue": elevator_id in OVERDUE_IDS,
        },
    )


@app.get("/fragments/close", response_class=HTMLResponse)
def close_panel() -> HTMLResponse:
    return HTMLResponse(content="")
