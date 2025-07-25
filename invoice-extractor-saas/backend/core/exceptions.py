"""
Custom exceptions and error handling for InvoiceAI
Provides GDPR-compliant error handling with proper audit logging
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType

logger = logging.getLogger(__name__)


class InvoiceAIException(Exception):
    """Base exception for InvoiceAI application"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or "INVOICEAI_ERROR"
        self.details = details or {}
        self.error_id = str(uuid.uuid4())
        super().__init__(self.message)


class AuthenticationError(InvoiceAIException):
    """Authentication related errors"""
    def __init__(self, message: str = "Authentication failed", details: Dict[str, Any] = None):
        super().__init__(message, "AUTH_ERROR", details)


class AuthorizationError(InvoiceAIException):
    """Authorization related errors"""
    def __init__(self, message: str = "Access denied", details: Dict[str, Any] = None):
        super().__init__(message, "AUTHZ_ERROR", details)


class ValidationError(InvoiceAIException):
    """Data validation errors"""
    def __init__(self, message: str = "Validation failed", details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class ProcessingError(InvoiceAIException):
    """Invoice processing errors"""
    def __init__(self, message: str = "Processing failed", details: Dict[str, Any] = None):
        super().__init__(message, "PROCESSING_ERROR", details)


class GDPRComplianceError(InvoiceAIException):
    """GDPR compliance related errors"""
    def __init__(self, message: str = "GDPR compliance violation", details: Dict[str, Any] = None):
        super().__init__(message, "GDPR_ERROR", details)


class DatabaseError(InvoiceAIException):
    """Database operation errors"""
    def __init__(self, message: str = "Database operation failed", details: Dict[str, Any] = None):
        super().__init__(message, "DATABASE_ERROR", details)


class ExternalServiceError(InvoiceAIException):
    """External service integration errors"""
    def __init__(self, message: str = "External service error", details: Dict[str, Any] = None):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


class FileProcessingError(InvoiceAIException):
    """File processing errors"""
    def __init__(self, message: str = "File processing failed", details: Dict[str, Any] = None):
        super().__init__(message, "FILE_PROCESSING_ERROR", details)


class RateLimitError(InvoiceAIException):
    """Rate limiting errors"""
    def __init__(self, message: str = "Rate limit exceeded", details: Dict[str, Any] = None):
        super().__init__(message, "RATE_LIMIT_ERROR", details)


def create_error_response(
    error: InvoiceAIException,
    status_code: int = 500,
    include_details: bool = False
) -> Dict[str, Any]:
    """Create standardized error response"""
    response = {
        "error": {
            "id": error.error_id,
            "code": error.error_code,
            "message": error.message,
            "timestamp": datetime.utcnow().isoformat(),
            "type": type(error).__name__
        }
    }
    
    # Include details only in development or for specific error types
    if include_details and error.details:
        response["error"]["details"] = error.details
    
    return response


async def log_error_event(
    error: Exception,
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
    """Log error events for audit and monitoring"""
    try:
        from core.database import async_session_maker
        
        async with async_session_maker() as db:
            error_details = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
                "request_url": str(request.url) if request else None,
                "request_method": request.method if request else None,
                "user_agent": request.headers.get("user-agent") if request else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if hasattr(error, 'error_id'):
                error_details["error_id"] = error.error_id
            
            if hasattr(error, 'error_code'):
                error_details["error_code"] = error.error_code
            
            # Determine risk level based on error type
            risk_level = "low"
            if isinstance(error, (AuthenticationError, AuthorizationError, GDPRComplianceError)):
                risk_level = "high"
            elif isinstance(error, (DatabaseError, ExternalServiceError)):
                risk_level = "medium"
            
            await log_audit_event(
                db=db,
                event_type=AuditEventType.BREACH_DETECTED if risk_level == "high" else AuditEventType.DATA_ACCESS,
                event_description=f"Application error: {str(error)}",
                user_id=uuid.UUID(user_id) if user_id else None,
                system_component="error_handler",
                risk_level=risk_level,
                operation_details=error_details,
                user_ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None
            )
            
    except Exception as logging_error:
        # Fallback to standard logging if database logging fails
        logger.error(f"Failed to log error event: {logging_error}")
        logger.error(f"Original error: {error}")


# Exception handlers for FastAPI
async def invoiceai_exception_handler(request: Request, exc: InvoiceAIException) -> JSONResponse:
    """Handle custom InvoiceAI exceptions"""
    
    # Log the error
    await log_error_event(exc, request, context={"endpoint": str(request.url)})
    
    # Determine status code based on exception type
    status_code = 500
    if isinstance(exc, AuthenticationError):
        status_code = 401
    elif isinstance(exc, AuthorizationError):
        status_code = 403
    elif isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, ProcessingError):
        status_code = 422
    elif isinstance(exc, GDPRComplianceError):
        status_code = 451  # Unavailable For Legal Reasons
    elif isinstance(exc, RateLimitError):
        status_code = 429
    
    # Create response (exclude sensitive details in production)
    include_details = False  # Set to True in development
    response_data = create_error_response(exc, status_code, include_details)
    
    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions"""
    
    error = InvoiceAIException(
        message=exc.detail if hasattr(exc, 'detail') else "HTTP error occurred",
        error_code="HTTP_ERROR"
    )
    
    await log_error_event(error, request, context={"status_code": exc.status_code})
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(error, exc.status_code)
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors"""
    
    validation_error = ValidationError(
        message="Request validation failed",
        details={
            "validation_errors": exc.errors(),
            "invalid_body": exc.body if hasattr(exc, 'body') else None
        }
    )
    
    await log_error_event(validation_error, request, context={"validation_details": exc.errors()})
    
    return JSONResponse(
        status_code=422,
        content=create_error_response(validation_error, 422, True)  # Include validation details
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors"""
    
    if isinstance(exc, IntegrityError):
        db_error = DatabaseError(
            message="Data integrity constraint violation",
            details={"constraint_violation": True}
        )
        status_code = 409  # Conflict
    else:
        db_error = DatabaseError(
            message="Database operation failed",
            details={"database_error": True}
        )
        status_code = 500
    
    await log_error_event(db_error, request, context={"sql_error": str(exc)})
    
    return JSONResponse(
        status_code=status_code,
        content=create_error_response(db_error, status_code)
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    
    general_error = InvoiceAIException(
        message="An unexpected error occurred",
        error_code="INTERNAL_ERROR",
        details={"exception_type": type(exc).__name__}
    )
    
    await log_error_event(general_error, request, context={"unexpected_error": str(exc)})
    
    # Log to standard logger as well for debugging
    logger.exception(f"Unexpected error in {request.url}: {exc}")
    
    return JSONResponse(
        status_code=500,
        content=create_error_response(general_error, 500)
    )


# Utility functions for error handling in routes
def handle_database_error(operation: str, error: Exception) -> InvoiceAIException:
    """Convert database errors to InvoiceAI exceptions"""
    if isinstance(error, IntegrityError):
        return DatabaseError(
            f"Database integrity error during {operation}",
            details={"operation": operation, "constraint_violation": True}
        )
    elif isinstance(error, SQLAlchemyError):
        return DatabaseError(
            f"Database error during {operation}",
            details={"operation": operation}
        )
    else:
        return InvoiceAIException(
            f"Unexpected error during {operation}",
            "OPERATION_ERROR",
            details={"operation": operation}
        )


def handle_processing_error(stage: str, error: Exception) -> ProcessingError:
    """Convert processing errors to ProcessingError exceptions"""
    return ProcessingError(
        f"Processing failed at stage: {stage}",
        details={
            "stage": stage,
            "original_error": str(error),
            "error_type": type(error).__name__
        }
    )


def handle_validation_error(field: str, value: Any, constraint: str) -> ValidationError:
    """Create validation error for specific field"""
    return ValidationError(
        f"Validation failed for field '{field}'",
        details={
            "field": field,
            "value": str(value) if value is not None else None,
            "constraint": constraint
        }
    )


def handle_gdpr_error(operation: str, reason: str) -> GDPRComplianceError:
    """Create GDPR compliance error"""
    return GDPRComplianceError(
        f"GDPR compliance issue in {operation}: {reason}",
        details={
            "operation": operation,
            "compliance_issue": reason,
            "gdpr_article": "multiple"  # Would be specific in real implementation
        }
    )