"""
api/main.py
-----------
The AgriMine API:  python -m api   (http://127.0.0.1:8000, docs at /docs, schema at /openapi.json)
Serves the prebuilt web app from web/out when it exists, so one process is the whole product.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import errors, lab, state
from api.schemas import ErrorBody, LabStatus
from api.routers import advice, checks, insights, meta, teachers

ROOT = Path(__file__).resolve().parent.parent
WEB_OUT = ROOT / "web" / "out"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.warm = state.warm_up()
    app.state.lab = lab.Lab()
    app.state.lab.start()                  # the technical lab (Streamlit) runs next to the API: one command, whole product
    yield
    app.state.lab.stop()


app = FastAPI(title="AgriMine API", version="1.0.0", lifespan=lifespan,
              description="Crop recommendation, soil health and Plan B for AgriMine. All logic lives in core/; this layer only validates and shapes.")
errors.install(app)
if os.environ.get("AGRIMINE_DEV"):      # development only: the Next dev server (port 3000) calls this API (port 8000)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])
ERROR_RESPONSES = {404: {"model": ErrorBody, "description": "Not found"}, 422: {"model": ErrorBody, "description": "Invalid input"}}
for router in (meta.router, checks.router, advice.router, insights.router, teachers.router):
    app.include_router(router, prefix="/api", responses=ERROR_RESPONSES)   # the contract shows the ONE error shape


@app.get("/api/lab", tags=["meta"], summary="Is the technical lab (Streamlit) up, and where is it?", response_model=LabStatus)
def lab_status(request: Request):
    """The web app links to the lab only when this says it answers. `url` uses the host the browser used to reach this API."""
    current = app.state.lab
    return {"available": current.available, "url": lab.url(request.url.hostname or "localhost"), "note": current.note}


@app.get("/api/health", tags=["meta"], summary="Liveness check")
def health():
    return {"status": "ok", **getattr(app.state, "warm", {})}


if WEB_OUT.exists():          # the product: the built web app, served by this same process
    app.mount("/", StaticFiles(directory=WEB_OUT, html=True), name="web")
