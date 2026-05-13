from __future__ import annotations
import math
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).parent
PAGE_SIZE = 10

app = FastAPI()
templates = Jinja2Templates(directory=str(BASE / "templates"))

DF: pd.DataFrame = pd.DataFrame()
EXPIRY: pd.Series = pd.Series(dtype="datetime64[ns]")


@app.on_event("startup")
def load_data() -> None:
    global DF, EXPIRY
    DF = pd.read_csv(BASE / "elevator_fleet.csv").sort_values("elevator_id").reset_index(drop=True)
    EXPIRY = pd.to_datetime(DF["license_expiry_date"], format="%d-%b-%y", errors="coerce")


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
            "sort_by": sort_by,
            "sort_dir": sort_dir,
        },
    )
