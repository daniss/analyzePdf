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


async def reset_invoice_review_status(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    user_id: uuid.UUID
) -> bool:
    """Mark invoice as exported after bulk export"""
    try:
        # Get the invoice first to verify ownership
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
        
        # Set status to exported instead of pending review
        await db.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(review_status="exported")
        )
        
        # Log the status change
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Marked invoice as exported after bulk export",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="export_system",
            risk_level="low"
        )
        
        return True
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_MODIFICATION,
            event_description=f"Failed to reset invoice review status: {str(e)}",
            user_id=user_id,
            invoice_id=invoice_id,
            system_component="export_system",
            risk_level="medium"
        )
        return False


# ==========================================
# DUPLICATE DETECTION FUNCTIONS
# ==========================================

async def find_duplicate_by_hash(
    db: AsyncSession,
    file_hash: str,
    user_id: uuid.UUID
) -> Optional[Invoice]:
    """
    Find existing invoice with the same file hash for duplicate detection
    
    Args:
        db: Database session
        file_hash: SHA-256 hash of the file content
        user_id: ID of the user to check duplicates for
        
    Returns:
        Invoice if duplicate found, None otherwise
    """
    try:
        query = select(Invoice).where(
            and_(
                Invoice.file_hash == file_hash,
                Invoice.data_controller_id == user_id,
                Invoice.processing_status != "deleted"
            )
        ).order_by(Invoice.created_at.desc())
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Error checking file hash duplicate: {str(e)}",
            user_id=user_id,
            system_component="duplicate_detector",
            risk_level="low"
        )
        return None


async def find_duplicates_by_invoice_key(
    db: AsyncSession,
    invoice_number: str,
    supplier_siret: str,
    user_id: uuid.UUID,
    exclude_invoice_id: Optional[uuid.UUID] = None
) -> List[Invoice]:
    """
    Find existing invoices with the same business key (invoice_number + supplier_siret)
    
    Args:
        db: Database session
        invoice_number: Invoice number from extracted data
        supplier_siret: Supplier SIRET number
        user_id: ID of the user to check duplicates for
        exclude_invoice_id: Invoice ID to exclude from search (for updates)
        
    Returns:
        List of invoices with matching business key
    """
    try:
        query = select(Invoice).where(
            and_(
                Invoice.data_controller_id == user_id,
                Invoice.processing_status.in_(["completed", "processing"]),
                Invoice.extracted_data_encrypted.isnot(None)
            )
        )
        
        if exclude_invoice_id:
            query = query.where(Invoice.id != exclude_invoice_id)
        
        query = query.order_by(Invoice.created_at.desc())
        
        result = await db.execute(query)
        all_invoices = result.scalars().all()
        
        # Filter by business key in extracted data
        matching_invoices = []
        
        for invoice in all_invoices:
            try:
                # Get decrypted extracted data
                extracted_data = await get_extracted_data(db, invoice.id, user_id)
                
                if extracted_data:
                    existing_invoice_number = extracted_data.invoice_number
                    existing_supplier_siret = None
                    
                    if extracted_data.vendor and extracted_data.vendor.siret_number:
                        existing_supplier_siret = extracted_data.vendor.siret_number
                    
                    # Match business key
                    if (existing_invoice_number == invoice_number and 
                        existing_supplier_siret == supplier_siret):
                        matching_invoices.append(invoice)
                        
            except Exception as e:
                # Skip invoices that can't be decrypted
                continue
        
        return matching_invoices
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Error checking invoice key duplicates: {str(e)}",
            user_id=user_id,
            system_component="duplicate_detector",
            risk_level="low"
        )
        return []


async def get_user_invoice_stats(
    db: AsyncSession,
    user_id: uuid.UUID,
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Get invoice processing statistics for duplicate analysis
    
    Args:
        db: Database session
        user_id: ID of the user
        days_back: Number of days to look back for statistics
        
    Returns:
        Dictionary with processing statistics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get basic counts
        total_query = select(Invoice).where(
            and_(
                Invoice.data_controller_id == user_id,
                Invoice.created_at >= cutoff_date,
                Invoice.processing_status != "deleted"
            )
        )
        
        result = await db.execute(total_query)
        recent_invoices = result.scalars().all()
        
        stats = {
            "total_invoices": len(recent_invoices),
            "completed_invoices": len([i for i in recent_invoices if i.processing_status == "completed"]),
            "processing_invoices": len([i for i in recent_invoices if i.processing_status == "processing"]),
            "failed_invoices": len([i for i in recent_invoices if i.processing_status == "failed"]),
            "unique_file_hashes": len(set(i.file_hash for i in recent_invoices)),
            "days_analyzed": days_back,
            "oldest_invoice": min(recent_invoices, key=lambda x: x.created_at).created_at if recent_invoices else None,
            "newest_invoice": max(recent_invoices, key=lambda x: x.created_at).created_at if recent_invoices else None
        }
        
        # Calculate potential file duplicates
        hash_counts = {}
        for invoice in recent_invoices:
            hash_counts[invoice.file_hash] = hash_counts.get(invoice.file_hash, 0) + 1
        
        stats["potential_file_duplicates"] = sum(1 for count in hash_counts.values() if count > 1)
        
        return stats
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Error getting user invoice stats: {str(e)}",
            user_id=user_id,
            system_component="duplicate_detector",
            risk_level="low"
        )
        return {
            "total_invoices": 0,
            "error": str(e)
        }


async def get_invoice_business_key(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    user_id: uuid.UUID
) -> Optional[str]:
    """
    Extract business key (invoice_number + supplier_siret) from an invoice
    
    Args:
        db: Database session
        invoice_id: ID of the invoice
        user_id: ID of the user (for access control)
        
    Returns:
        Business key string or None if not available
    """
    try:
        extracted_data = await get_extracted_data(db, invoice_id, user_id)
        
        if not extracted_data:
            return None
        
        invoice_number = extracted_data.invoice_number
        supplier_siret = None
        
        if extracted_data.vendor and extracted_data.vendor.siret_number:
            supplier_siret = extracted_data.vendor.siret_number
        
        if invoice_number and supplier_siret:
            return f"{supplier_siret}_{invoice_number}"
        
        return None
        
    except Exception as e:
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Error extracting business key for invoice {invoice_id}: {str(e)}",
            user_id=user_id,
            system_component="duplicate_detector",
            risk_level="low"
        )
        return None