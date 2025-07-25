"""
GDPR Helper functions to bridge CRUD operations with existing GDPR modules
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

from models.gdpr_models import AuditLog, AuditEventType
from core.gdpr_encryption import gdpr_encryption


async def log_audit_event(
    db: AsyncSession,
    event_type: AuditEventType,
    event_description: str,
    user_id: Optional[uuid.UUID] = None,
    data_subject_id: Optional[uuid.UUID] = None,
    invoice_id: Optional[uuid.UUID] = None,
    system_component: str = "api",
    legal_basis: Optional[str] = None,
    processing_purpose: Optional[str] = None,
    data_categories_accessed: Optional[List[str]] = None,
    risk_level: str = "low",
    operation_details: Optional[Dict[str, Any]] = None,
    compliance_notes: Optional[str] = None,
    user_ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None
) -> str:
    """
    Log audit event using async database session
    """
    try:
        audit_log = AuditLog(
            event_type=event_type,
            event_description=event_description,
            user_id=user_id,
            data_subject_id=data_subject_id,
            invoice_id=invoice_id,
            system_component=system_component,
            legal_basis=legal_basis,
            processing_purpose=processing_purpose,
            data_categories_accessed=data_categories_accessed,
            risk_level=risk_level,
            operation_details=operation_details,
            compliance_notes=compliance_notes,
            user_ip_address=user_ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        
        db.add(audit_log)
        # Don't commit here - let the calling function handle it
        await db.flush()  # Just get the ID
        
        return str(audit_log.id)
        
    except Exception as e:
        raise Exception(f"Failed to log audit event: {str(e)}")


def encrypt_data(data: str, purpose: str = "data_storage") -> str:
    """
    Encrypt personal data using the existing GDPR encryption service
    """
    if not data:
        return None
    
    try:
        result = gdpr_encryption.encrypt_personal_data(data, purpose)
        return result["encrypted_data"]
    except Exception as e:
        raise Exception(f"Failed to encrypt data: {str(e)}")


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt personal data using the existing GDPR encryption service
    """
    if not encrypted_data:
        return None
    
    try:
        return gdpr_encryption.decrypt_personal_data(encrypted_data)
    except Exception as e:
        raise Exception(f"Failed to decrypt data: {str(e)}")


def encrypt_json_data(data: Dict[str, Any], purpose: str = "data_storage") -> str:
    """
    Encrypt JSON data using the existing GDPR encryption service
    """
    if not data:
        return None
    
    try:
        result = gdpr_encryption.encrypt_json_data(data, purpose)
        return result["encrypted_data"]
    except Exception as e:
        raise Exception(f"Failed to encrypt JSON data: {str(e)}")


def decrypt_json_data(encrypted_data: str) -> Dict[str, Any]:
    """
    Decrypt JSON data using the existing GDPR encryption service
    """
    if not encrypted_data:
        return None
    
    try:
        return gdpr_encryption.decrypt_json_data(encrypted_data)
    except Exception as e:
        raise Exception(f"Failed to decrypt JSON data: {str(e)}")