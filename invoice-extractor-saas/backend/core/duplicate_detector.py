"""
Smart Duplicate Detection Service for French Invoice Processing

This module provides comprehensive duplicate detection for file uploads and invoice processing,
specifically designed for French accounting workflows with expert-comptable requirements.

Features:
- File-level duplicate detection using SHA-256 hashes
- Invoice-level duplicate detection using supplier SIRET + invoice number
- French business logic for legitimate reprocessing scenarios
- GDPR-compliant audit logging
- Batch processing support with user choice handling
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from fastapi import UploadFile

from models.gdpr_models import Invoice
from schemas.invoice import InvoiceData
from core.gdpr_helpers import log_audit_event
from models.gdpr_models import AuditEventType

logger = logging.getLogger(__name__)


class DuplicateType(Enum):
    """Types of duplicates that can be detected"""
    FILE_DUPLICATE = "file_duplicate"
    INVOICE_DUPLICATE = "invoice_duplicate"
    CROSS_PERIOD_DUPLICATE = "cross_period_duplicate"


class DuplicateSeverity(Enum):
    """Severity levels for duplicate detection"""
    ERROR = "error"          # Must be resolved, blocks processing
    WARNING = "warning"      # Should be resolved, allows processing with confirmation
    INFO = "info"           # Informational only, processing continues


class DuplicateAction(Enum):
    """Actions that can be taken for duplicates"""
    SKIP = "skip"                    # Skip the duplicate file
    REPLACE = "replace"              # Replace the existing invoice
    ALLOW = "allow"                  # Allow both (legitimate reprocessing)
    USER_CHOICE = "user_choice"      # Let user decide


@dataclass
class DuplicateResult:
    """Result of duplicate detection for a single item"""
    is_duplicate: bool
    duplicate_type: Optional[DuplicateType] = None
    severity: DuplicateSeverity = DuplicateSeverity.INFO
    existing_invoice_id: Optional[uuid.UUID] = None
    existing_filename: Optional[str] = None
    existing_created_at: Optional[datetime] = None
    french_message: str = ""
    recommended_action: DuplicateAction = DuplicateAction.SKIP
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BatchDuplicateReport:
    """Report of duplicate detection for a batch of files"""
    total_files: int
    unique_files: int
    file_duplicates: List[Tuple[str, DuplicateResult]]  # filename -> result
    invoice_duplicates: List[Tuple[str, DuplicateResult]]  # filename -> result
    requires_user_action: bool
    french_summary: str
    processing_recommendations: Dict[str, DuplicateAction]

    @property
    def duplicate_count(self) -> int:
        return len(self.file_duplicates) + len(self.invoice_duplicates)


class DuplicateDetector:
    """
    Professional duplicate detection service for French invoice processing
    
    Handles both file-level and business-logic duplicates with French accounting best practices
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def check_file_duplicate(
        self, 
        file_hash: str, 
        user_id: uuid.UUID, 
        filename: str = ""
    ) -> DuplicateResult:
        """
        Check if a file with the same hash already exists for this user
        
        Args:
            file_hash: SHA-256 hash of the file content
            user_id: ID of the user uploading the file
            filename: Original filename for better error messages
            
        Returns:
            DuplicateResult with detection details
        """
        try:
            # Query for existing invoice with same file hash
            query = select(Invoice).where(
                and_(
                    Invoice.file_hash == file_hash,
                    Invoice.data_controller_id == user_id,
                    Invoice.processing_status != "deleted"
                )
            )
            result = await self.db.execute(query)
            existing_invoice = result.scalar_one_or_none()
            
            if existing_invoice:
                self.logger.info(f"File duplicate detected: {filename} matches {existing_invoice.filename}")
                
                return DuplicateResult(
                    is_duplicate=True,
                    duplicate_type=DuplicateType.FILE_DUPLICATE,
                    severity=DuplicateSeverity.WARNING,
                    existing_invoice_id=existing_invoice.id,
                    existing_filename=existing_invoice.filename,
                    existing_created_at=existing_invoice.created_at,
                    french_message=f"Le fichier '{filename}' est identique au fichier '{existing_invoice.filename}' déjà traité le {existing_invoice.created_at.strftime('%d/%m/%Y à %H:%M')}.",
                    recommended_action=DuplicateAction.SKIP,
                    metadata={
                        "existing_processing_status": existing_invoice.processing_status,
                        "file_size": existing_invoice.file_size,
                        "days_since_upload": (datetime.utcnow() - existing_invoice.created_at).days
                    }
                )
            
            # No duplicate found
            return DuplicateResult(
                is_duplicate=False,
                french_message=f"Fichier '{filename}' unique - prêt pour traitement."
            )
            
        except Exception as e:
            self.logger.error(f"Error checking file duplicate for {filename}: {str(e)}")
            return DuplicateResult(
                is_duplicate=False,
                severity=DuplicateSeverity.ERROR,
                french_message=f"Erreur lors de la vérification des doublons pour '{filename}': {str(e)}"
            )
    
    async def check_invoice_duplicate(
        self, 
        invoice_data: InvoiceData, 
        user_id: uuid.UUID,
        filename: str = ""
    ) -> DuplicateResult:
        """
        Check if an invoice with the same business key already exists
        
        Business key = supplier SIRET + invoice number (French standard)
        
        Args:
            invoice_data: Extracted invoice data
            user_id: ID of the user processing the invoice
            filename: Original filename for better error messages
            
        Returns:
            DuplicateResult with detection details
        """
        try:
            # Extract business key components
            invoice_number = invoice_data.invoice_number
            supplier_siret = None
            
            if invoice_data.vendor and invoice_data.vendor.siret_number:
                supplier_siret = invoice_data.vendor.siret_number
            
            # Skip check if we don't have enough data
            if not invoice_number or not supplier_siret:
                return DuplicateResult(
                    is_duplicate=False,
                    french_message=f"Vérification des doublons ignorée pour '{filename}' - données insuffisantes (numéro facture ou SIRET manquant)."
                )
            
            # Build business key for comparison
            business_key = f"{supplier_siret}_{invoice_number}"
            
            # Query for existing invoices with same business key
            # Look for invoices where extracted data contains the same invoice number and SIRET
            query = select(Invoice).where(
                and_(
                    Invoice.data_controller_id == user_id,
                    Invoice.processing_status.in_(["completed", "processing"]),
                    Invoice.extracted_data_encrypted.isnot(None)  # Has processed data
                )
            )
            result = await self.db.execute(query)
            existing_invoices = result.scalars().all()
            
            # Check each existing invoice's extracted data
            for existing_invoice in existing_invoices:
                try:
                    # Get the decrypted invoice data
                    from crud.invoice import get_extracted_data
                    existing_data = await get_extracted_data(self.db, existing_invoice.id, user_id)
                    
                    if existing_data:
                        existing_invoice_number = existing_data.invoice_number
                        existing_supplier_siret = None
                        
                        if existing_data.vendor and existing_data.vendor.siret_number:
                            existing_supplier_siret = existing_data.vendor.siret_number
                        
                        existing_business_key = f"{existing_supplier_siret}_{existing_invoice_number}"
                        
                        if business_key == existing_business_key:
                            # Found a duplicate!
                            days_ago = (datetime.utcnow() - existing_invoice.created_at).days
                            
                            # Determine severity based on time gap
                            if days_ago < 7:
                                severity = DuplicateSeverity.ERROR
                                action = DuplicateAction.USER_CHOICE
                                message = f"⚠️ DOUBLON DÉTECTÉ: La facture {invoice_number} de {invoice_data.vendor.name or 'ce fournisseur'} (SIRET: {supplier_siret}) a déjà été traitée il y a {days_ago} jour(s). Action requise."
                            elif days_ago < 30:
                                severity = DuplicateSeverity.WARNING
                                action = DuplicateAction.USER_CHOICE
                                message = f"⚠️ Facture {invoice_number} déjà traitée il y a {days_ago} jour(s). Retraitement possible (correction comptable?)."
                            else:
                                severity = DuplicateSeverity.INFO
                                action = DuplicateAction.ALLOW
                                message = f"ℹ️ Facture {invoice_number} traitée il y a {days_ago} jour(s). Retraitement autorisé (nouvel exercice comptable?)."
                            
                            return DuplicateResult(
                                is_duplicate=True,
                                duplicate_type=DuplicateType.CROSS_PERIOD_DUPLICATE if days_ago >= 30 else DuplicateType.INVOICE_DUPLICATE,
                                severity=severity,
                                existing_invoice_id=existing_invoice.id,
                                existing_filename=existing_invoice.filename,
                                existing_created_at=existing_invoice.created_at,
                                french_message=message,
                                recommended_action=action,
                                metadata={
                                    "business_key": business_key,
                                    "days_since_processing": days_ago,
                                    "existing_status": existing_invoice.processing_status,
                                    "supplier_name": invoice_data.vendor.name if invoice_data.vendor else "",
                                    "invoice_amount": invoice_data.total_ttc or invoice_data.total or 0
                                }
                            )
                            
                except Exception as e:
                    self.logger.warning(f"Error checking existing invoice {existing_invoice.id}: {str(e)}")
                    continue
            
            # No duplicate found
            return DuplicateResult(
                is_duplicate=False,
                french_message=f"Facture {invoice_number} unique - traitement autorisé."
            )
            
        except Exception as e:
            self.logger.error(f"Error checking invoice duplicate for {filename}: {str(e)}")
            return DuplicateResult(
                is_duplicate=False,
                severity=DuplicateSeverity.ERROR,
                french_message=f"Erreur lors de la vérification des doublons métier pour '{filename}': {str(e)}"
            )
    
    async def get_batch_duplicates(
        self, 
        files: List[UploadFile], 
        user_id: uuid.UUID
    ) -> BatchDuplicateReport:
        """
        Analyze a batch of files for duplicates before processing
        
        Args:
            files: List of uploaded files
            user_id: ID of the user uploading files
            
        Returns:
            BatchDuplicateReport with comprehensive duplicate analysis
        """
        try:
            self.logger.info(f"Starting batch duplicate analysis for {len(files)} files")
            
            file_duplicates = []
            invoice_duplicates = []
            unique_files = 0
            processing_recommendations = {}
            
            # First pass: Check for file duplicates
            file_hashes = {}
            
            for file in files:
                try:
                    # Calculate file hash
                    content = await file.read()
                    file_hash = hashlib.sha256(content).hexdigest()
                    await file.seek(0)  # Reset file pointer
                    
                    # Check for duplicate within this batch
                    if file_hash in file_hashes:
                        # Duplicate within batch
                        result = DuplicateResult(
                            is_duplicate=True,
                            duplicate_type=DuplicateType.FILE_DUPLICATE,
                            severity=DuplicateSeverity.WARNING,
                            french_message=f"Fichier '{file.filename}' identique à '{file_hashes[file_hash]}' dans ce lot.",
                            recommended_action=DuplicateAction.SKIP
                        )
                        file_duplicates.append((file.filename, result))
                        processing_recommendations[file.filename] = DuplicateAction.SKIP
                        continue
                    
                    file_hashes[file_hash] = file.filename
                    
                    # Check against database
                    duplicate_result = await self.check_file_duplicate(file_hash, user_id, file.filename)
                    
                    if duplicate_result.is_duplicate:
                        file_duplicates.append((file.filename, duplicate_result))
                        processing_recommendations[file.filename] = duplicate_result.recommended_action
                    else:
                        unique_files += 1
                        processing_recommendations[file.filename] = DuplicateAction.ALLOW
                        
                except Exception as e:
                    self.logger.error(f"Error processing file {file.filename}: {str(e)}")
                    continue
            
            # Generate French summary
            total_files = len(files)
            duplicate_count = len(file_duplicates) + len(invoice_duplicates)
            
            if duplicate_count == 0:
                french_summary = f"✅ {total_files} fichier(s) unique(s) détecté(s) - prêt pour traitement."
            else:
                french_summary = f"⚠️ {unique_files} fichier(s) unique(s), {duplicate_count} doublon(s) détecté(s). Action requise pour les doublons."
            
            # Determine if user action is required
            requires_user_action = any(
                result.severity in [DuplicateSeverity.ERROR, DuplicateSeverity.WARNING]
                for _, result in file_duplicates + invoice_duplicates
            )
            
            report = BatchDuplicateReport(
                total_files=total_files,
                unique_files=unique_files,
                file_duplicates=file_duplicates,
                invoice_duplicates=invoice_duplicates,
                requires_user_action=requires_user_action,
                french_summary=french_summary,
                processing_recommendations=processing_recommendations
            )
            
            self.logger.info(f"Batch duplicate analysis completed: {report.french_summary}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error in batch duplicate analysis: {str(e)}")
            return BatchDuplicateReport(
                total_files=len(files),
                unique_files=0,
                file_duplicates=[],
                invoice_duplicates=[],
                requires_user_action=True,
                french_summary=f"❌ Erreur lors de l'analyse des doublons: {str(e)}",
                processing_recommendations={}
            )
    
    async def log_duplicate_resolution(
        self,
        original_invoice_id: Optional[uuid.UUID],
        duplicate_file_hash: str,
        duplicate_invoice_key: str,
        detection_type: DuplicateType,
        user_action: DuplicateAction,
        user_id: uuid.UUID,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Log duplicate detection and resolution for audit purposes
        
        Args:
            original_invoice_id: ID of the original invoice (if exists)
            duplicate_file_hash: Hash of the duplicate file
            duplicate_invoice_key: Business key of duplicate invoice
            detection_type: Type of duplicate detected
            user_action: Action taken by user
            user_id: ID of the user making the decision
            metadata: Additional context information
        """
        try:
            await log_audit_event(
                db=self.db,
                event_type=AuditEventType.DATA_PROCESSING,
                event_description=f"Duplicate detection and resolution: {detection_type.value}",
                user_id=user_id,
                invoice_id=original_invoice_id,
                system_component="duplicate_detector",
                legal_basis="legitimate_interest",
                processing_purpose="duplicate_prevention",
                data_categories_accessed=["business_data"],
                risk_level="low" if user_action in [DuplicateAction.SKIP, DuplicateAction.ALLOW] else "medium",
                operation_details={
                    "detection_type": detection_type.value,
                    "user_action": user_action.value,
                    "duplicate_file_hash": duplicate_file_hash[:16] + "...",  # Truncate for privacy
                    "duplicate_invoice_key": duplicate_invoice_key,
                    "metadata": metadata or {}
                }
            )
            
            self.logger.info(f"Logged duplicate resolution: {detection_type.value} -> {user_action.value}")
            
        except Exception as e:
            self.logger.error(f"Error logging duplicate resolution: {str(e)}")
    
    async def ensure_unique_invoices_for_export(
        self,
        invoices: List[InvoiceData],
        user_id: uuid.UUID
    ) -> Tuple[List[InvoiceData], List[str]]:
        """
        Ensure no duplicate invoices are included in export batch
        
        Critical for Sage PNM exports to prevent accounting errors
        
        Args:
            invoices: List of invoice data to export
            user_id: ID of the user performing export
            
        Returns:
            Tuple of (unique_invoices, duplicate_warnings)
        """
        try:
            unique_invoices = []
            seen_business_keys = set()
            duplicate_warnings = []
            
            for invoice in invoices:
                # Build business key
                invoice_number = invoice.invoice_number or "SANS_NUMERO"
                supplier_siret = ""
                
                if invoice.vendor and invoice.vendor.siret_number:
                    supplier_siret = invoice.vendor.siret_number
                
                business_key = f"{supplier_siret}_{invoice_number}"
                
                if business_key in seen_business_keys:
                    # Duplicate found in export batch
                    supplier_name = invoice.vendor.name if invoice.vendor else "Fournisseur inconnu"
                    warning = f"⚠️ Doublon retiré de l'export: Facture {invoice_number} de {supplier_name} (SIRET: {supplier_siret})"
                    duplicate_warnings.append(warning)
                    
                    self.logger.warning(f"Removed duplicate from export: {business_key}")
                    continue
                
                seen_business_keys.add(business_key)
                unique_invoices.append(invoice)
            
            # Log export deduplication
            if duplicate_warnings:
                await log_audit_event(
                    db=self.db,
                    event_type=AuditEventType.DATA_EXPORT,
                    event_description=f"Export deduplication: {len(duplicate_warnings)} duplicates removed",
                    user_id=user_id,
                    system_component="duplicate_detector",
                    legal_basis="legitimate_interest", 
                    processing_purpose="export_validation",
                    data_categories_accessed=["business_data"],
                    risk_level="low",
                    operation_details={
                        "original_count": len(invoices),
                        "unique_count": len(unique_invoices),
                        "duplicates_removed": len(duplicate_warnings),
                        "warnings": duplicate_warnings
                    }
                )
            
            self.logger.info(f"Export deduplication: {len(invoices)} -> {len(unique_invoices)} invoices")
            return unique_invoices, duplicate_warnings
            
        except Exception as e:
            self.logger.error(f"Error in export deduplication: {str(e)}")
            # Return original list on error to avoid blocking exports
            return invoices, [f"❌ Erreur lors de la déduplication: {str(e)}"]


# Convenience functions for easy import
async def create_duplicate_detector(db: AsyncSession) -> DuplicateDetector:
    """Factory function to create a duplicate detector instance"""
    return DuplicateDetector(db)


async def check_file_hash_duplicate(
    db: AsyncSession, 
    file_hash: str, 
    user_id: uuid.UUID
) -> bool:
    """Quick check if a file hash already exists - for simple use cases"""
    detector = DuplicateDetector(db)
    result = await detector.check_file_duplicate(file_hash, user_id)
    return result.is_duplicate