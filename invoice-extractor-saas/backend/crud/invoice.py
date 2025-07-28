"""
Invoice CRUD operations with GDPR compliance and encryption
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete, update
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
import uuid
import json
import hashlib
from datetime import datetime

from models.gdpr_models import Invoice, DataSubject, InvoiceDataSubject, AuditEventType, AuditLog
from core.gdpr_helpers import encrypt_json_data, decrypt_json_data, log_audit_event


async def create_invoice(
    db: AsyncSession,
    filename: str,
    file_content: bytes,
    mime_type: str,
    data_controller_id: uuid.UUID,
    processing_purposes: List[str],
    legal_basis: str = "legitimate_interest",
    processing_source: str = "individual",
    batch_id: Optional[str] = None
) -> Invoice:
    """Create new invoice with encrypted storage and audit logging"""
    try:
        # Calculate file hash for integrity verification
        file_hash = hashlib.sha256(file_content).hexdigest()
        file_size = len(file_content)
        
        # Create invoice record
        invoice = Invoice(
            filename=filename,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=mime_type,
            processing_status="pending",
            legal_basis=legal_basis,
            processing_purposes=processing_purposes,
            data_controller_id=data_controller_id,
            transferred_to_third_country=True,  # Claude API in US
            transfer_mechanism="standard_contractual_clauses",
            processing_source=processing_source,
            batch_id=batch_id
        )
        
        # Add to database
        db.add(invoice)
        await db.flush()  # Get ID without committing
        
        # Log invoice creation
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Invoice uploaded: {filename}",
            user_id=data_controller_id,
            invoice_id=invoice.id,
            system_component="invoice_crud",
            legal_basis=legal_basis,
            processing_purpose="invoice_processing",
            data_categories_accessed=["business_data"],
            risk_level="low",
            operation_details={
                "filename": filename,
                "file_size": file_size,
                "mime_type": mime_type
            }
        )
        
        await db.commit()
        await db.refresh(invoice)
        return invoice
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed invoice creation: {str(e)}",
            user_id=data_controller_id,
            system_component="invoice_crud",
            risk_level="high"
        )
        raise


async def get_invoice_by_id(
    db: AsyncSession, 
    invoice_id: uuid.UUID, 
    user_id: uuid.UUID,
    include_data_subjects: bool = False
) -> Optional[Invoice]:
    """Get invoice by ID with access control and audit logging"""
    try:
        query = select(Invoice).where(
            and_(
                Invoice.id == invoice_id,
                Invoice.data_controller_id == user_id  # Access control
            )
        )
        
        if include_data_subjects:
            query = query.options(selectinload(Invoice.data_subjects))
        
        result = await db.execute(query)
        invoice = result.scalar_one_or_none()
        
        if invoice:
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Invoice accessed: {invoice.filename}",
                user_id=user_id,
                invoice_id=invoice_id,
                system_component="invoice_crud",
                risk_level="low"
            )
        
        return invoice
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed invoice access: {str(e)}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            risk_level="medium"
        )
        raise


async def get_user_invoices(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None
) -> List[Invoice]:
    """Get invoices for a user with pagination and filtering"""
    try:
        query = select(Invoice).where(Invoice.data_controller_id == user_id)
        
        if status_filter:
            query = query.where(Invoice.processing_status == status_filter)
        
        query = query.offset(skip).limit(limit).order_by(Invoice.created_at.desc())
        
        result = await db.execute(query)
        invoices = result.scalars().all()
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Invoice list accessed ({len(invoices)} records)",
            user_id=user_id,
            system_component="invoice_crud",
            risk_level="low",
            operation_details={
                "count": len(invoices),
                "skip": skip,
                "limit": limit,
                "status_filter": status_filter
            }
        )
        
        return invoices
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed invoice list access: {str(e)}",
            user_id=user_id,
            system_component="invoice_crud",
            risk_level="medium"
        )
        raise


async def update_invoice_status(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    status: str,
    user_id: uuid.UUID,
    processing_started_at: Optional[datetime] = None,
    processing_completed_at: Optional[datetime] = None,
    error_message: Optional[str] = None
) -> Optional[Invoice]:
    """Update invoice processing status with audit logging"""
    try:
        result = await db.execute(
            select(Invoice).where(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.data_controller_id == user_id
                )
            )
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return None
        
        old_status = invoice.processing_status
        invoice.processing_status = status
        
        if processing_started_at:
            invoice.processing_started_at = processing_started_at
        if processing_completed_at:
            invoice.processing_completed_at = processing_completed_at
        if error_message:
            invoice.error_message = error_message
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Invoice status updated: {old_status} -> {status}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            risk_level="low",
            operation_details={
                "old_status": old_status,
                "new_status": status
            }
        )
        
        await db.commit()
        await db.refresh(invoice)
        return invoice
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed invoice status update: {str(e)}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            risk_level="medium"
        )
        raise


async def store_extracted_data(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    extracted_data: Dict[str, Any],
    user_id: uuid.UUID
) -> Optional[Invoice]:
    """Store extracted invoice data with encryption and audit logging"""
    try:
        result = await db.execute(
            select(Invoice).where(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.data_controller_id == user_id
                )
            )
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return None
        
        # Encrypt the extracted data
        encrypted_data = encrypt_json_data(extracted_data, "invoice_data_extraction")
        invoice.extracted_data_encrypted = encrypted_data
        invoice.processing_status = "completed"
        invoice.processing_completed_at = datetime.utcnow()
        
        # Set review status for individual invoices
        if hasattr(invoice, 'review_status') and not invoice.batch_id:
            invoice.review_status = "pending_review"
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Invoice data extracted and stored: {invoice.filename}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            legal_basis=invoice.legal_basis,
            processing_purpose="data_extraction",
            data_categories_accessed=["business_data", "financial_data"],
            risk_level="medium",
            operation_details={
                "data_fields": list(extracted_data.keys()) if extracted_data else []
            }
        )
        
        await db.commit()
        await db.refresh(invoice)
        return invoice
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed to store extracted data: {str(e)}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            risk_level="high"
        )
        raise


async def get_extracted_data(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    """Retrieve and decrypt extracted invoice data with audit logging"""
    try:
        result = await db.execute(
            select(Invoice).where(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.data_controller_id == user_id
                )
            )
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice or not invoice.extracted_data_encrypted:
            return None
        
        # Decrypt the data
        extracted_data = decrypt_json_data(invoice.extracted_data_encrypted)
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Invoice extracted data accessed: {invoice.filename}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            risk_level="low"
        )
        
        return extracted_data
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed to access extracted data: {str(e)}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            risk_level="medium"
        )
        raise


async def delete_invoice(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    user_id: uuid.UUID,
    deletion_reason: str = "user_request"
) -> bool:
    """Delete invoice with GDPR compliance and audit logging"""
    try:
        result = await db.execute(
            select(Invoice).where(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.data_controller_id == user_id
                )
            )
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return False
        
        # Store filename for audit log before deletion
        filename = invoice.filename
        
        # Delete associated data subject relationships
        await db.execute(
            delete(InvoiceDataSubject).where(
                InvoiceDataSubject.invoice_id == invoice_id
            )
        )
        
        # Update audit logs to set invoice_id to NULL before deletion to avoid foreign key violations
        await db.execute(
            update(AuditLog).where(
                AuditLog.invoice_id == invoice_id
            ).values(invoice_id=None)
        )
        
        # Delete the invoice
        await db.delete(invoice)
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_DELETION,
            event_description=f"Invoice deleted: {filename}. Reason: {deletion_reason}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            legal_basis="user_request",
            processing_purpose="data_deletion",
            risk_level="medium",
            operation_details={
                "filename": filename,
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
            event_description=f"Failed invoice deletion: {str(e)}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="invoice_crud",
            risk_level="high"
        )
        raise


async def link_invoice_to_data_subject(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    data_subject_id: uuid.UUID,
    role_in_invoice: str,
    user_id: uuid.UUID
) -> InvoiceDataSubject:
    """Link invoice to data subject with audit logging"""
    try:
        # Create the relationship
        relationship = InvoiceDataSubject(
            invoice_id=invoice_id,
            data_subject_id=data_subject_id,
            role_in_invoice=role_in_invoice
        )
        
        db.add(relationship)
        
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Invoice linked to data subject (role: {role_in_invoice})",
            user_id=user_id,
            invoice_id=invoice_id,
            data_subject_id=data_subject_id,
            system_component="invoice_crud",
            legal_basis="legitimate_interest",
            processing_purpose="data_relationship_management",
            risk_level="low",
            operation_details={
                "role": role_in_invoice
            }
        )
        
        await db.commit()
        await db.refresh(relationship)
        return relationship
        
    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed to link invoice to data subject: {str(e)}",
            user_id=user_id,
            invoice_id=invoice_id,
            data_subject_id=data_subject_id,
            system_component="invoice_crud",
            risk_level="medium"
        )
        raise