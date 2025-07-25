"""
GDPR Audit and Compliance Service
Implements comprehensive audit logging for GDPR Article 30 compliance
Provides audit trails for all personal data processing activities
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from contextlib import asynccontextmanager
import asyncio
from fastapi import Request
import logging

from core.database import get_db
from models.gdpr_models import (
    AuditLog, AuditEventType, DataSubject, Invoice, 
    BreachIncident, ConsentRecord
)
from models.user import User


class GDPRAuditService:
    """
    Comprehensive audit service for GDPR compliance
    Tracks all personal data processing activities
    """
    
    def __init__(self):
        self.logger = logging.getLogger("gdpr_audit")
        
    async def log_data_access(
        self,
        user_id: str,
        data_subject_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
        purpose: str = None,
        legal_basis: str = None,
        data_categories: List[str] = None,
        request: Optional[Request] = None,
        db: Session = None
    ) -> str:
        """
        Log data access event for GDPR Article 30 compliance
        
        Args:
            user_id: ID of user accessing data
            data_subject_id: ID of data subject whose data is accessed
            invoice_id: ID of invoice being accessed
            purpose: Processing purpose
            legal_basis: GDPR Article 6 legal basis
            data_categories: Categories of data accessed
            request: HTTP request object for context
            db: Database session
            
        Returns:
            Audit log ID
        """
        try:
            audit_log = AuditLog(
                id=uuid.uuid4(),
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Data access for purpose: {purpose}",
                user_id=uuid.UUID(user_id) if user_id else None,
                data_subject_id=uuid.UUID(data_subject_id) if data_subject_id else None,
                invoice_id=uuid.UUID(invoice_id) if invoice_id else None,
                processing_purpose=purpose,
                legal_basis=legal_basis,
                data_categories_accessed=data_categories,
                system_component="api",
                user_ip_address=self._get_client_ip(request) if request else None,
                user_agent=request.headers.get("user-agent") if request else None,
                session_id=self._get_session_id(request) if request else None,
                risk_level="low"
            )
            
            if db:
                db.add(audit_log)
                db.commit()
                return str(audit_log.id)
            else:
                async with self._get_db_session() as session:
                    session.add(audit_log)
                    await session.commit()
                    return str(audit_log.id)
                    
        except Exception as e:
            self.logger.error(f"Failed to log data access: {str(e)}")
            raise
    
    async def log_data_modification(
        self,
        user_id: str,
        data_subject_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
        modification_details: Dict[str, Any] = None,
        purpose: str = None,
        legal_basis: str = None,
        request: Optional[Request] = None,
        db: Session = None
    ) -> str:
        """
        Log data modification event
        
        Args:
            user_id: ID of user modifying data
            data_subject_id: ID of affected data subject
            invoice_id: ID of modified invoice
            modification_details: Details of modifications made
            purpose: Processing purpose
            legal_basis: GDPR legal basis
            request: HTTP request context
            db: Database session
            
        Returns:
            Audit log ID
        """
        try:
            audit_log = AuditLog(
                id=uuid.uuid4(),
                event_type=AuditEventType.DATA_MODIFICATION,
                event_description=f"Data modification: {modification_details.get('summary', 'Data updated')}",
                user_id=uuid.UUID(user_id) if user_id else None,
                data_subject_id=uuid.UUID(data_subject_id) if data_subject_id else None,
                invoice_id=uuid.UUID(invoice_id) if invoice_id else None,
                processing_purpose=purpose,
                legal_basis=legal_basis,
                system_component="api",
                operation_details=modification_details,
                user_ip_address=self._get_client_ip(request) if request else None,
                user_agent=request.headers.get("user-agent") if request else None,
                session_id=self._get_session_id(request) if request else None,
                risk_level="medium"
            )
            
            if db:
                db.add(audit_log)
                db.commit()
                return str(audit_log.id)
            else:
                async with self._get_db_session() as session:
                    session.add(audit_log)
                    await session.commit()
                    return str(audit_log.id)
                    
        except Exception as e:
            self.logger.error(f"Failed to log data modification: {str(e)}")
            raise
    
    async def log_data_deletion(
        self,
        user_id: str,
        data_subject_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
        deletion_reason: str = None,
        retention_policy_applied: bool = False,
        request: Optional[Request] = None,
        db: Session = None
    ) -> str:
        """
        Log data deletion event for right to erasure compliance
        
        Args:
            user_id: ID of user performing deletion
            data_subject_id: ID of data subject whose data is deleted
            invoice_id: ID of deleted invoice
            deletion_reason: Reason for deletion
            retention_policy_applied: Whether deletion was due to retention policy
            request: HTTP request context
            db: Database session
            
        Returns:
            Audit log ID
        """
        try:
            event_type = (AuditEventType.RETENTION_POLICY_APPLIED 
                         if retention_policy_applied 
                         else AuditEventType.DATA_DELETION)
            
            audit_log = AuditLog(
                id=uuid.uuid4(),
                event_type=event_type,
                event_description=f"Data deletion: {deletion_reason}",
                user_id=uuid.UUID(user_id) if user_id else None,
                data_subject_id=uuid.UUID(data_subject_id) if data_subject_id else None,
                invoice_id=uuid.UUID(invoice_id) if invoice_id else None,
                system_component="retention_service" if retention_policy_applied else "api",
                operation_details={
                    "deletion_reason": deletion_reason,
                    "retention_policy_applied": retention_policy_applied
                },
                user_ip_address=self._get_client_ip(request) if request else None,
                user_agent=request.headers.get("user-agent") if request else None,
                session_id=self._get_session_id(request) if request else None,
                risk_level="high"  # Deletion is high-impact event
            )
            
            if db:
                db.add(audit_log)
                db.commit()
                return str(audit_log.id)
            else:
                async with self._get_db_session() as session:
                    session.add(audit_log)
                    await session.commit()
                    return str(audit_log.id)
                    
        except Exception as e:
            self.logger.error(f"Failed to log data deletion: {str(e)}")
            raise
    
    async def log_data_export(
        self,
        user_id: str,
        data_subject_id: str,
        export_format: str,
        data_categories: List[str] = None,
        purpose: str = "data_portability_request",
        request: Optional[Request] = None,
        db: Session = None
    ) -> str:
        """
        Log data export event for data portability compliance
        
        Args:
            user_id: ID of user performing export
            data_subject_id: ID of data subject whose data is exported
            export_format: Format of export (JSON, CSV, etc.)
            data_categories: Categories of data exported
            purpose: Purpose of export
            request: HTTP request context
            db: Database session
            
        Returns:
            Audit log ID
        """
        try:
            audit_log = AuditLog(
                id=uuid.uuid4(),
                event_type=AuditEventType.DATA_EXPORT,
                event_description=f"Data export in {export_format} format",
                user_id=uuid.UUID(user_id) if user_id else None,
                data_subject_id=uuid.UUID(data_subject_id) if data_subject_id else None,
                processing_purpose=purpose,
                legal_basis="data_portability_right",
                data_categories_accessed=data_categories,
                system_component="export_service",
                operation_details={
                    "export_format": export_format,
                    "data_categories": data_categories
                },
                user_ip_address=self._get_client_ip(request) if request else None,
                user_agent=request.headers.get("user-agent") if request else None,
                session_id=self._get_session_id(request) if request else None,
                risk_level="medium"
            )
            
            if db:
                db.add(audit_log)
                db.commit()
                return str(audit_log.id)
            else:
                async with self._get_db_session() as session:
                    session.add(audit_log)
                    await session.commit()
                    return str(audit_log.id)
                    
        except Exception as e:
            self.logger.error(f"Failed to log data export: {str(e)}")
            raise
    
    async def log_consent_event(
        self,
        data_subject_id: str,
        consent_given: bool,
        consent_purposes: List[str],
        consent_mechanism: str = "web_form",
        user_id: Optional[str] = None,
        request: Optional[Request] = None,
        db: Session = None
    ) -> str:
        """
        Log consent given or withdrawn event
        
        Args:
            data_subject_id: ID of data subject
            consent_given: True if consent given, False if withdrawn
            consent_purposes: Purposes for which consent was given/withdrawn  
            consent_mechanism: How consent was obtained
            user_id: ID of user if applicable
            request: HTTP request context
            db: Database session
            
        Returns:
            Audit log ID
        """
        try:
            event_type = (AuditEventType.CONSENT_GIVEN 
                         if consent_given 
                         else AuditEventType.CONSENT_WITHDRAWN)
            
            audit_log = AuditLog(
                id=uuid.uuid4(),
                event_type=event_type,
                event_description=f"Consent {'given' if consent_given else 'withdrawn'} for: {', '.join(consent_purposes)}",
                user_id=uuid.UUID(user_id) if user_id else None,
                data_subject_id=uuid.UUID(data_subject_id),
                processing_purpose=", ".join(consent_purposes),
                legal_basis="consent",
                system_component="consent_service",
                operation_details={
                    "consent_given": consent_given,
                    "consent_purposes": consent_purposes,
                    "consent_mechanism": consent_mechanism
                },
                user_ip_address=self._get_client_ip(request) if request else None,
                user_agent=request.headers.get("user-agent") if request else None,
                session_id=self._get_session_id(request) if request else None,
                risk_level="medium"
            )
            
            if db:
                db.add(audit_log)
                db.commit()
                return str(audit_log.id)
            else:
                async with self._get_db_session() as session:
                    session.add(audit_log)
                    await session.commit()
                    return str(audit_log.id)
                    
        except Exception as e:
            self.logger.error(f"Failed to log consent event: {str(e)}")
            raise
    
    async def log_breach_detected(
        self,
        breach_type: str,
        severity: str,
        affected_data_categories: List[str],
        estimated_affected_subjects: int = None,
        discovery_details: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        db: Session = None
    ) -> str:
        """
        Log data breach detection event
        
        Args:
            breach_type: Type of breach (confidentiality, integrity, availability)
            severity: Severity level (low, medium, high, critical)
            affected_data_categories: Categories of data affected
            estimated_affected_subjects: Number of affected data subjects
            discovery_details: Details about how breach was discovered
            user_id: ID of user reporting breach
            db: Database session
            
        Returns:
            Audit log ID
        """
        try:
            audit_log = AuditLog(
                id=uuid.uuid4(),
                event_type=AuditEventType.BREACH_DETECTED,
                event_description=f"{severity.upper()} {breach_type} breach detected",
                user_id=uuid.UUID(user_id) if user_id else None,
                system_component="security_monitoring",
                operation_details={
                    "breach_type": breach_type,
                    "severity": severity,
                    "affected_data_categories": affected_data_categories,
                    "estimated_affected_subjects": estimated_affected_subjects,
                    "discovery_details": discovery_details
                },
                risk_level="critical",
                compliance_notes="GDPR Article 33/34 notification required"
            )
            
            if db:
                db.add(audit_log)
                db.commit()
                return str(audit_log.id)
            else:
                async with self._get_db_session() as session:
                    session.add(audit_log)
                    await session.commit()
                    return str(audit_log.id)
                    
        except Exception as e:
            self.logger.error(f"Failed to log breach detection: {str(e)}")
            raise
    
    async def get_audit_trail(
        self,
        data_subject_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_types: List[AuditEventType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for compliance reporting
        
        Args:
            data_subject_id: Filter by data subject
            invoice_id: Filter by invoice
            user_id: Filter by user
            event_types: Filter by event types
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of records
            db: Database session
            
        Returns:
            List of audit log records
        """
        try:
            if not db:
                async with self._get_db_session() as db:
                    return await self._query_audit_trail(
                        db, data_subject_id, invoice_id, user_id,
                        event_types, start_date, end_date, limit
                    )
            else:
                return await self._query_audit_trail(
                    db, data_subject_id, invoice_id, user_id,
                    event_types, start_date, end_date, limit
                )
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit trail: {str(e)}")
            raise
    
    async def _query_audit_trail(
        self,
        db: Session,
        data_subject_id: Optional[str],
        invoice_id: Optional[str], 
        user_id: Optional[str],
        event_types: List[AuditEventType],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Internal method to query audit trail"""
        
        query = db.query(AuditLog)
        
        # Apply filters
        if data_subject_id:
            query = query.filter(AuditLog.data_subject_id == uuid.UUID(data_subject_id))
        
        if invoice_id:
            query = query.filter(AuditLog.invoice_id == uuid.UUID(invoice_id))
        
        if user_id:
            query = query.filter(AuditLog.user_id == uuid.UUID(user_id))
        
        if event_types:
            query = query.filter(AuditLog.event_type.in_(event_types))
        
        if start_date:
            query = query.filter(AuditLog.event_timestamp >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.event_timestamp <= end_date)
        
        # Order by timestamp descending and limit
        audit_logs = query.order_by(desc(AuditLog.event_timestamp)).limit(limit).all()
        
        # Convert to dictionaries
        result = []
        for log in audit_logs:
            result.append({
                "id": str(log.id),
                "event_type": log.event_type.value,
                "event_description": log.event_description,
                "event_timestamp": log.event_timestamp.isoformat(),
                "user_id": str(log.user_id) if log.user_id else None,
                "data_subject_id": str(log.data_subject_id) if log.data_subject_id else None,
                "invoice_id": str(log.invoice_id) if log.invoice_id else None,
                "processing_purpose": log.processing_purpose,
                "legal_basis": log.legal_basis,
                "data_categories_accessed": log.data_categories_accessed,
                "system_component": log.system_component,
                "operation_details": log.operation_details,
                "risk_level": log.risk_level,
                "compliance_notes": log.compliance_notes
            })
        
        return result
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request"""
        if not request:
            return None
        
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request"""
        if not request:
            return None
        
        # Check for session cookie or header
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = request.headers.get("x-session-id")
        
        return session_id
    
    @asynccontextmanager
    async def _get_db_session(self):
        """Get database session for async operations"""
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()


# Global audit service instance
gdpr_audit = GDPRAuditService()