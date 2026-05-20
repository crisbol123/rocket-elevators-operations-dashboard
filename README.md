# Rocket Elevators Operations Dashboard

Rocket Elevators Operations Dashboard is a monorepo for building an internal operations dashboard that combines a frontend prototype, data exploration notebooks, and shared datasets to support fleet monitoring and decision-making.

## Repository Structure
- /platform: HTML and frontend code for the operations dashboard UI.
- /intelligence: Notebooks and Python scripts for analytics, modeling, and insights.
- /data: Datasets used by the platform and intelligence workflows.
- /docs: Specifications, reports, and project documentation.

## Running the dashboard

```bash
cd platform && python3 -m uvicorn server:app --reload
```

Dashboard available at `http://localhost:8000/`.

## Development notes

**Artificial request delay:** `server.py` includes a middleware that adds a 200 ms delay to every request so the loading spinner is visible during local development (responses are otherwise near-instant). Remove or disable the `dev_delay` middleware before deploying to production.

```python
# Remove this block before deploying:
@app.middleware("http")
async def dev_delay(request: Request, call_next):
    await asyncio.sleep(0.2)
    return await call_next(request)
```
