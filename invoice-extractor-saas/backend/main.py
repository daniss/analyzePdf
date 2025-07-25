from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import uvicorn

from api import auth, invoices, exports, gdpr_rights  # gdpr_compliance
from core.config import settings
from core.exceptions import (
    InvoiceAIException, invoiceai_exception_handler,
    http_exception_handler, validation_exception_handler,
    sqlalchemy_exception_handler, general_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up InvoiceAI API...")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="InvoiceAI API",
    description="AI-powered PDF invoice data extraction API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(exports.router, prefix="/api/exports", tags=["exports"])
# app.include_router(gdpr_compliance.router, prefix="/api", tags=["gdpr-compliance"])
app.include_router(gdpr_rights.router, prefix="/api", tags=["gdpr-rights"])

# Register exception handlers
app.add_exception_handler(InvoiceAIException, invoiceai_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/")
async def root():
    return {"message": "InvoiceAI API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )