from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import uvicorn

from api import auth, invoices, export_routes, gdpr_rights, batch_processing, admin_costs, pcg_routes, validation_reports, auto_correction_routes, siret_validation_routes, admin, payments
from core.monitoring import get_health_status, get_metrics
from core.config import settings
from core.exceptions import (
    ComptaFlowException, comptaflow_exception_handler,
    http_exception_handler, validation_exception_handler,
    sqlalchemy_exception_handler, general_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up ComptaFlow API...")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="ComptaFlow API",
    description="Plateforme intelligente d'extraction de données de factures pour experts-comptables",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - More permissive for debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3000",
        "https://comptaflow.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(batch_processing.router, prefix="/api/batch", tags=["batch-processing"])
# WebSocket support removed - simplified to polling-based updates
app.include_router(export_routes.router, prefix="/api/exports", tags=["exports"])
# app.include_router(gdpr_compliance.router, prefix="/api", tags=["gdpr-compliance"])
app.include_router(gdpr_rights.router, prefix="/api", tags=["gdpr-rights"])
app.include_router(admin_costs.router, prefix="/api/admin/costs", tags=["admin-costs"])
app.include_router(admin.router, prefix="/api/admin/system", tags=["admin-system"])
app.include_router(pcg_routes.router, tags=["plan-comptable-general"])
app.include_router(validation_reports.router, tags=["validation-reports"])
app.include_router(auto_correction_routes.router, tags=["auto-correction"])
app.include_router(siret_validation_routes.router, prefix="/api/siret", tags=["siret-validation"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])

# Register exception handlers
app.add_exception_handler(ComptaFlowException, comptaflow_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/")
async def root():
    return {"message": "ComptaFlow API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check for monitoring systems"""
    return await get_health_status()


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus-style metrics endpoint"""
    metrics_text = await get_metrics()
    return PlainTextResponse(content=metrics_text, media_type="text/plain")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )