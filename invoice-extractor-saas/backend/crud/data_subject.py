"""
Data Subject CRUD operations with GDPR compliance and encryption
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from models.gdpr_models import (
    DataSubject, DataSubjectType, ProcessingPurpose, DataCategory,
    RetentionStatus, AuditEventType, ConsentRecord
)
from core.gdpr_helpers import encrypt_data, decrypt_data, log_audit_event


async def create_data_subject(
    db: AsyncSession,
    name: str,
    email: Optional[str],
    phone: Optional[str],
    address: Optional[str],
    data_subject_type: DataSubjectType,
    processing_purposes: List[ProcessingPurpose],
    data_categories: List[DataCategory],
    legal_basis: str,
    created_by: uuid.UUID,
    consent_given: bool = False
) -> DataSubject:
    """Create new data subject with encrypted PII and audit logging"""
    try:
        # Encrypt PII fields
        name_encrypted = encrypt_data(name)
        email_encrypted = encrypt_data(email) if email else None
        phone_encrypted = encrypt_data(phone) if phone else None
        address_encrypted = encrypt_data(address) if address else None
        
        # Convert enums to JSON-serializable format
        processing_purposes_json = [purpose.value for purpose in processing_purposes]
        data_categories_json = [category.value for category in data_categories]
        
        # Create data subject
        data_subject = DataSubject(
            name_encrypted=name_encrypted,
            email_encrypted=email_encrypted,
            phone_encrypted=phone_encrypted,
            address_encrypted=address_encrypted,
            data_subject_type=data_subject_type,
            processing_purposes=processing_purposes_json,
            data_categories=data_categories_json,
            legal_basis=legal_basis,
            created_by=created_by,
            consent_given=consent_given,
            consent_date=datetime.utcnow() if consent_given else None
        )
        
        db.add(data_subject)
        await db.flush()  # Get ID without committing
        
        # Log data subject creation
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Data subject created: {data_subject_type.value}",
            user_id=created_by,
            data_subject_id=data_subject.id,
            system_component="data_subject_crud",
            legal_basis=legal_basis,
            processing_purpose="data_subject_management",
            data_categories_accessed=data_categories_json,
            risk_level="medium",
            operation_details={
                "data_subject_type": data_subject_type.value,
                "processing_purposes": processing_purposes_json,
                "consent_given": consent_given
            }
        )
        
        await db.commit()
        await db.refresh(data_subject)
        return data_subject
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed data subject creation: {str(e)}",
            user_id=created_by,
            system_component="data_subject_crud",
            risk_level="high"
        )
        raise


async def get_data_subject_by_id(
    db: AsyncSession,
    data_subject_id: uuid.UUID,
    user_id: uuid.UUID,
    decrypt_pii: bool = False
) -> Optional[DataSubject]:
    """Get data subject by ID with optional PII decryption and audit logging"""
    try:
        result = await db.execute(
            select(DataSubject).where(
                and_(
                    DataSubject.id == data_subject_id,
                    DataSubject.created_by == user_id  # Access control
                )
            )
        )
        data_subject = result.scalar_one_or_none()
        
        if data_subject:
            # Decrypt PII if requested and authorized
            if decrypt_pii:
                # Create a decrypted copy for return (don't modify the DB object)
                data_subject.decrypted_name = decrypt_data(data_subject.name_encrypted)
                if data_subject.email_encrypted:
                    data_subject.decrypted_email = decrypt_data(data_subject.email_encrypted)
                if data_subject.phone_encrypted:
                    data_subject.decrypted_phone = decrypt_data(data_subject.phone_encrypted)
                if data_subject.address_encrypted:
                    data_subject.decrypted_address = decrypt_data(data_subject.address_encrypted)
            
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Data subject accessed (PII decrypted: {decrypt_pii})",
                user_id=user_id,
                data_subject_id=data_subject_id,
                system_component="data_subject_crud",
                risk_level="medium" if decrypt_pii else "low",
                operation_details={"decrypt_pii": decrypt_pii}
            )
        
        return data_subject
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed data subject access: {str(e)}",
            user_id=user_id,
            data_subject_id=data_subject_id,
            system_component="data_subject_crud",
            risk_level="medium"
        )
        raise


async def search_data_subjects(
    db: AsyncSession,
    user_id: uuid.UUID,
    data_subject_type: Optional[DataSubjectType] = None,
    processing_purpose: Optional[ProcessingPurpose] = None,
    retention_status: Optional[RetentionStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[DataSubject]:
    """Search data subjects with filtering and audit logging"""
    try:
        query = select(DataSubject).where(DataSubject.created_by == user_id)
        
        if data_subject_type:
            query = query.where(DataSubject.data_subject_type == data_subject_type)
        
        if processing_purpose:
            # Search in JSON array for processing purpose
            query = query.where(
                DataSubject.processing_purposes.contains([processing_purpose.value])
            )
        
        if retention_status:
            query = query.where(DataSubject.retention_status == retention_status)
        
        query = query.offset(skip).limit(limit).order_by(DataSubject.created_at.desc())
        
        result = await db.execute(query)
        data_subjects = result.scalars().all()
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Data subjects searched ({len(data_subjects)} results)",
            user_id=user_id,
            system_component="data_subject_crud",
            risk_level="low",
            operation_details={
                "count": len(data_subjects),
                "filters": {
                    "data_subject_type": data_subject_type.value if data_subject_type else None,
                    "processing_purpose": processing_purpose.value if processing_purpose else None,
                    "retention_status": retention_status.value if retention_status else None
                }
            }
        )
        
        return data_subjects
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed data subjects search: {str(e)}",
            user_id=user_id,
            system_component="data_subject_crud",
            risk_level="medium"
        )
        raise


async def update_data_subject(
    db: AsyncSession,
    data_subject_id: uuid.UUID,
    user_id: uuid.UUID,
    **kwargs
) -> Optional[DataSubject]:
    """Update data subject with encryption and audit logging"""
    try:
        result = await db.execute(
            select(DataSubject).where(
                and_(
                    DataSubject.id == data_subject_id,
                    DataSubject.created_by == user_id
                )
            )
        )
        data_subject = result.scalar_one_or_none()
        
        if not data_subject:
            return None
        
        updated_fields = []
        
        # Handle PII fields that need encryption
        pii_fields = {
            'name': 'name_encrypted',
            'email': 'email_encrypted',
            'phone': 'phone_encrypted',
            'address': 'address_encrypted'
        }
        
        for field, encrypted_field in pii_fields.items():
            if field in kwargs:
                value = kwargs[field]
                if value:
                    encrypted_value = encrypt_data(value)
                    setattr(data_subject, encrypted_field, encrypted_value)
                    updated_fields.append(field)
                else:
                    setattr(data_subject, encrypted_field, None)
                    updated_fields.append(field)
        
        # Handle non-PII fields
        for key, value in kwargs.items():
            if key not in pii_fields and hasattr(data_subject, key):
                if getattr(data_subject, key) != value:
                    setattr(data_subject, key, value)
                    updated_fields.append(key)
        
        if updated_fields:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Data subject updated. Fields: {', '.join(updated_fields)}",
                user_id=user_id,
                data_subject_id=data_subject_id,
                system_component="data_subject_crud",
                risk_level="medium",
                operation_details={"updated_fields": updated_fields}
            )
            
            await db.commit()
            await db.refresh(data_subject)
        
        return data_subject
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed data subject update: {str(e)}",
            user_id=user_id,
            data_subject_id=data_subject_id,
            system_component="data_subject_crud",
            risk_level="high"
        )
        raise


async def delete_data_subject(
    db: AsyncSession,
    data_subject_id: uuid.UUID,
    user_id: uuid.UUID,
    deletion_reason: str = "user_request"
) -> bool:
    """Delete data subject with GDPR compliance and audit logging"""
    try:
        result = await db.execute(
            select(DataSubject).where(
                and_(
                    DataSubject.id == data_subject_id,
                    DataSubject.created_by == user_id
                )
            )
        )
        data_subject = result.scalar_one_or_none()
        
        if not data_subject:
            return False
        
        # Store info for audit log before deletion
        data_subject_type = data_subject.data_subject_type.value
        
        # Delete the data subject (cascade will handle related records)
        await db.delete(data_subject)
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_DELETION,
            event_description=f"Data subject deleted: {data_subject_type}. Reason: {deletion_reason}",
            user_id=user_id,
            data_subject_id=data_subject_id,
            system_component="data_subject_crud",
            legal_basis="user_request",
            processing_purpose="data_deletion",
            risk_level="high",
            operation_details={
                "data_subject_type": data_subject_type,
                "deletion_reason": deletion_reason
            }
        )
        
        await db.commit()
        return True
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_DELETION,
            event_description=f"Failed data subject deletion: {str(e)}",
            user_id=user_id,
            data_subject_id=data_subject_id,
            system_component="data_subject_crud",
            risk_level="high"
        )
        raise


async def withdraw_consent(
    db: AsyncSession,
    data_subject_id: uuid.UUID,
    user_id: uuid.UUID,
    withdrawal_reason: Optional[str] = None
) -> Optional[DataSubject]:
    """Withdraw consent for data subject with audit logging"""
    try:
        result = await db.execute(
            select(DataSubject).where(
                and_(
                    DataSubject.id == data_subject_id,
                    DataSubject.created_by == user_id
                )
            )
        )
        data_subject = result.scalar_one_or_none()
        
        if not data_subject:
            return None
        
        # Update consent status
        data_subject.consent_withdrawn = True
        data_subject.consent_withdrawal_date = datetime.utcnow()
        
        # Create consent record for audit trail
        consent_record = ConsentRecord(
            data_subject_id=data_subject_id,
            consent_purposes=data_subject.processing_purposes,
            consent_mechanism="api_withdrawal",
            consent_text="Consent withdrawn via API",
            is_active=False,
            consent_given_date=data_subject.consent_date or datetime.utcnow(),
            consent_withdrawn_date=datetime.utcnow(),
            withdrawal_reason=withdrawal_reason
        )
        
        db.add(consent_record)
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.CONSENT_WITHDRAWN,
            event_description=f"Consent withdrawn for data subject. Reason: {withdrawal_reason or 'Not specified'}",
            user_id=user_id,
            data_subject_id=data_subject_id,
            system_component="data_subject_crud",
            legal_basis="consent_withdrawal",
            processing_purpose="consent_management",
            risk_level="medium",
            operation_details={
                "withdrawal_reason": withdrawal_reason,
                "processing_purposes": data_subject.processing_purposes
            }
        )
        
        await db.commit()
        await db.refresh(data_subject)
        return data_subject
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.CONSENT_WITHDRAWN,
            event_description=f"Failed consent withdrawal: {str(e)}",
            user_id=user_id,
            data_subject_id=data_subject_id,
            system_component="data_subject_crud",
            risk_level="high"
        )
        raise


async def export_data_subject_data(
    db: AsyncSession,
    data_subject_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    """Export all data for a data subject (GDPR Article 20 - Data Portability)"""
    try:
        result = await db.execute(
            select(DataSubject).where(
                and_(
                    DataSubject.id == data_subject_id,
                    DataSubject.created_by == user_id
                )
            ).options(selectinload(DataSubject.invoices))
        )
        data_subject = result.scalar_one_or_none()
        
        if not data_subject:
            return None
        
        # Decrypt PII for export
        export_data = {
            "data_subject_id": str(data_subject.id),
            "data_subject_type": data_subject.data_subject_type.value,
            "personal_data": {
                "name": decrypt_data(data_subject.name_encrypted),
                "email": decrypt_data(data_subject.email_encrypted) if data_subject.email_encrypted else None,
                "phone": decrypt_data(data_subject.phone_encrypted) if data_subject.phone_encrypted else None,
                "address": decrypt_data(data_subject.address_encrypted) if data_subject.address_encrypted else None,
            },
            "processing_information": {
                "processing_purposes": data_subject.processing_purposes,
                "data_categories": data_subject.data_categories,
                "legal_basis": data_subject.legal_basis,
                "consent_given": data_subject.consent_given,
                "consent_date": data_subject.consent_date.isoformat() if data_subject.consent_date else None,
                "consent_withdrawn": data_subject.consent_withdrawn,
                "consent_withdrawal_date": data_subject.consent_withdrawal_date.isoformat() if data_subject.consent_withdrawal_date else None,
            },
            "retention_information": {
                "retention_status": data_subject.retention_status.value,
                "retention_until": data_subject.retention_until.isoformat() if data_subject.retention_until else None,
            },
            "metadata": {
                "created_at": data_subject.created_at.isoformat(),
                "updated_at": data_subject.updated_at.isoformat() if data_subject.updated_at else None,
                "source_system": data_subject.source_system,
            },
            "related_invoices": [
                {
                    "invoice_id": str(invoice.id),
                    "filename": invoice.filename,
                    "created_at": invoice.created_at.isoformat(),
                    "processing_status": invoice.processing_status
                }
                for invoice in data_subject.invoices
            ]
        }
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_EXPORT,
            event_description="Data subject data exported for portability request",
            user_id=user_id,
            data_subject_id=data_subject_id,
            system_component="data_subject_crud",
            legal_basis="data_portability_request",
            processing_purpose="data_export",
            risk_level="high",
            operation_details={
                "export_format": "json",
                "includes_pii": True,
                "related_invoices_count": len(data_subject.invoices)
            }
        )
        
        return export_data
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_EXPORT,
            event_description=f"Failed data subject export: {str(e)}",
            user_id=user_id,
            data_subject_id=data_subject_id,
            system_component="data_subject_crud",
            risk_level="high"
        )
        raise