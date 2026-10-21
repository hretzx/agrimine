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

DEFAULT_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "https://agrimine.vercel.app"]


def cors_settings(environ=os.environ) -> dict:
    """
    Which web origins may call the API from a browser. Set AGRIMINE_CORS_ORIGINS (comma separated, no path) to change the list
    without touching the code, and AGRIMINE_CORS_ORIGIN_REGEX to also allow a pattern such as Vercel's preview addresses
    (for example https://agrimine-.*\\.vercel\\.app). An empty AGRIMINE_CORS_ORIGINS allows no cross-origin access at all.
    """
    raw = environ.get("AGRIMINE_CORS_ORIGINS")
    origins = DEFAULT_ORIGINS if raw is None else [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    return {"allow_origins": origins, "allow_origin_regex": environ.get("AGRIMINE_CORS_ORIGIN_REGEX") or None}


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
# CORS: the web app and the API are one origin when this process serves web/out, but they are two origins when the web app is hosted
# elsewhere (Vercel) or run by the Next dev server (port 3000). The browser then sends an OPTIONS "preflight" first and only calls the API
# if the answer carries Access-Control-Allow-Origin. Added AFTER errors.install(), so it is the outermost layer: every answer, errors included, gets the headers.
app.add_middleware(CORSMiddleware, **cors_settings(), allow_methods=["*"], allow_headers=["*"], allow_credentials=False)   # no cookies are used, so no credentials
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
    commit = os.environ.get("RENDER_GIT_COMMIT")      # Render sets this on every deploy: it says which commit is really running
    return {"status": "ok", **({"commit": commit[:7]} if commit else {}), **getattr(app.state, "warm", {})}


if WEB_OUT.exists():          # the product: the built web app, served by this same process
    app.mount("/", StaticFiles(directory=WEB_OUT, html=True), name="web")
