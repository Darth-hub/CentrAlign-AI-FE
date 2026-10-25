"""Standalone API for Netlify's frontend. Run on a persistent Python/container host."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from services.database import initialize
from services.auth import claims_from_header, current_claims
from security.routes import authorize

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title="ARIA portable procurement API", version="1.0.0", lifespan=lifespan)

@app.middleware("http")
async def authenticate(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path == "/api/health":
        return await call_next(request)
    try:
        claims = claims_from_header(request.headers.get("authorization"))
        authorize(request.method, request.url.path, claims["p2p_role"])
        request.state.claims = claims
        token = current_claims.set(claims)
        try: return await call_next(request)
        finally: current_claims.reset(token)
    except HTTPException as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)

# Register CORS outside auth so browser clients can read authentication errors.
app.add_middleware(CORSMiddleware,
    allow_origins=[x.strip() for x in settings.allowed_origins.split(",") if x.strip()],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"], allow_credentials=False)

from api import agents, admin, dashboard, decisions, config_view, invoices, chat, lifecycle, errors, runs
for prefix, module in [("agents", agents), ("agents", runs), ("admin", admin), ("dashboard", dashboard),
    ("decisions", decisions), ("config", config_view), ("invoices", invoices), ("chat", chat),
    ("lifecycle", lifecycle), ("errors", errors)]:
    app.include_router(module.router, prefix=f"/api/{prefix}")
from adapters.canonical_api import app as erp_app
app.mount("/api/erp", erp_app)

@app.get("/api/health")
def health():
    return {"status": "ok", "runtime": "portable", "model_provider": settings.llm_provider}
