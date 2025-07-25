"""
Audit Log CRUD operations for GDPR compliance monitoring
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, between
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta

from models.gdpr_models import AuditLog, AuditEventType


async def get_audit_logs(
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
    data_subject_id: Optional[uuid.UUID] = None,
    invoice_id: Optional[uuid.UUID] = None,
    event_type: Optional[AuditEventType] = None,
    system_component: Optional[str] = None,
    risk_level: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    requesting_user_id: Optional[uuid.UUID] = None
) -> List[AuditLog]:
    """Get audit logs with comprehensive filtering"""
    try:
        query = select(AuditLog)
        
        # Build filters
        filters = []
        
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        
        if data_subject_id:
            filters.append(AuditLog.data_subject_id == data_subject_id)
        
        if invoice_id:
            filters.append(AuditLog.invoice_id == invoice_id)
        
        if event_type:
            filters.append(AuditLog.event_type == event_type)
        
        if system_component:
            filters.append(AuditLog.system_component == system_component)
        
        if risk_level:
            filters.append(AuditLog.risk_level == risk_level)
        
        if start_date and end_date:
            filters.append(between(AuditLog.event_timestamp, start_date, end_date))
        elif start_date:
            filters.append(AuditLog.event_timestamp >= start_date)
        elif end_date:
            filters.append(AuditLog.event_timestamp <= end_date)
        
        # Apply filters
        if filters:
            query = query.where(and_(*filters))
        
        # Order and paginate
        query = query.order_by(desc(AuditLog.event_timestamp)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        # Log the audit access if we have a requesting user
        if requesting_user_id:
            from core.gdpr_helpers import log_audit_event
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Audit logs accessed ({len(logs)} records)",
                user_id=requesting_user_id,
                system_component="audit_log_crud",
                risk_level="medium",
                operation_details={
                    "count": len(logs),
                    "filters": {
                        "user_id": str(user_id) if user_id else None,
                        "data_subject_id": str(data_subject_id) if data_subject_id else None,
                        "invoice_id": str(invoice_id) if invoice_id else None,
                        "event_type": event_type.value if event_type else None,
                        "system_component": system_component,
                        "risk_level": risk_level,
                        "date_range": f"{start_date} to {end_date}" if start_date or end_date else None
                    }
                }
            )
        
        return logs
        
    except Exception as e:
        if requesting_user_id:
            from core.gdpr_helpers import log_audit_event
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Failed audit logs access: {str(e)}",
                user_id=requesting_user_id,
                system_component="audit_log_crud",
                risk_level="high"
            )
        raise


async def get_audit_log_by_id(
    db: AsyncSession,
    log_id: uuid.UUID,
    requesting_user_id: uuid.UUID
) -> Optional[AuditLog]:
    """Get specific audit log by ID"""
    try:
        result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
        log = result.scalar_one_or_none()
        
        if log:
            from core.gdpr_helpers import log_audit_event
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Specific audit log accessed: {log_id}",
                user_id=requesting_user_id,
                system_component="audit_log_crud",
                risk_level="medium"
            )
        
        return log
        
    except Exception as e:
        from core.gdpr_helpers import log_audit_event
        await log_audit_event(
            db=db,
            event_type=AuditEventType.DATA_ACCESS,
            event_description=f"Failed specific audit log access: {str(e)}",
            user_id=requesting_user_id,
            system_component="audit_log_crud",
            risk_level="high"
        )
        raise


async def get_audit_statistics(
    db: AsyncSession,
    user_id: Optional[uuid.UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    requesting_user_id: Optional[uuid.UUID] = None
) -> Dict[str, Any]:
    """Get audit log statistics for compliance reporting"""
    try:
        # Base query
        base_query = select(AuditLog)
        
        # Apply filters
        filters = []
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        
        if start_date and end_date:
            filters.append(between(AuditLog.event_timestamp, start_date, end_date))
        elif start_date:
            filters.append(AuditLog.event_timestamp >= start_date)
        elif end_date:
            filters.append(AuditLog.event_timestamp <= end_date)
        
        if filters:
            base_query = base_query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count(AuditLog.id)).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total_logs = total_result.scalar()
        
        # Get event type distribution
        event_type_query = select(
            AuditLog.event_type,
            func.count(AuditLog.id).label('count')
        ).group_by(AuditLog.event_type)
        
        if filters:
            event_type_query = event_type_query.where(and_(*filters))
        
        event_type_result = await db.execute(event_type_query)
        event_type_distribution = {
            row.event_type.value: row.count for row in event_type_result
        }
        
        # Get risk level distribution
        risk_level_query = select(
            AuditLog.risk_level,
            func.count(AuditLog.id).label('count')
        ).group_by(AuditLog.risk_level)
        
        if filters:
            risk_level_query = risk_level_query.where(and_(*filters))
        
        risk_level_result = await db.execute(risk_level_query)
        risk_level_distribution = {
            row.risk_level: row.count for row in risk_level_result
        }
        
        # Get system component distribution
        component_query = select(
            AuditLog.system_component,
            func.count(AuditLog.id).label('count')
        ).group_by(AuditLog.system_component)
        
        if filters:
            component_query = component_query.where(and_(*filters))
        
        component_result = await db.execute(component_query)
        component_distribution = {
            row.system_component: row.count for row in component_result
        }
        
        # Get recent high-risk events
        high_risk_query = select(AuditLog).where(
            AuditLog.risk_level.in_(['high', 'critical'])
        )
        
        if filters:
            high_risk_query = high_risk_query.where(and_(*filters))
        
        high_risk_query = high_risk_query.order_by(desc(AuditLog.event_timestamp)).limit(10)
        high_risk_result = await db.execute(high_risk_query)
        high_risk_events = high_risk_result.scalars().all()
        
        statistics = {
            "total_logs": total_logs,
            "event_type_distribution": event_type_distribution,
            "risk_level_distribution": risk_level_distribution,
            "system_component_distribution": component_distribution,
            "recent_high_risk_events": [
                {
                    "id": str(log.id),
                    "event_type": log.event_type.value,
                    "event_description": log.event_description,
                    "event_timestamp": log.event_timestamp.isoformat(),
                    "risk_level": log.risk_level,
                    "system_component": log.system_component
                }
                for log in high_risk_events
            ],
            "query_parameters": {
                "user_id": str(user_id) if user_id else None,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
        # Log the statistics access
        if requesting_user_id:
            from core.gdpr_helpers import log_audit_event
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description="Audit statistics generated for compliance reporting",
                user_id=requesting_user_id,
                system_component="audit_log_crud",
                risk_level="low",
                operation_details={
                    "total_logs": total_logs,
                    "query_user_id": str(user_id) if user_id else None
                }
            )
        
        return statistics
        
    except Exception as e:
        if requesting_user_id:
            from core.gdpr_helpers import log_audit_event
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_ACCESS,
                event_description=f"Failed audit statistics generation: {str(e)}",
                user_id=requesting_user_id,
                system_component="audit_log_crud",
                risk_level="high"
            )
        raise


async def cleanup_old_audit_logs(
    db: AsyncSession,
    retention_days: int = 2555,  # 7 years for French accounting compliance
    batch_size: int = 1000
) -> int:
    """Clean up old audit logs according to retention policy"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Count logs to be deleted
        count_query = select(func.count(AuditLog.id)).where(
            AuditLog.event_timestamp < cutoff_date
        )
        count_result = await db.execute(count_query)
        total_to_delete = count_result.scalar()
        
        if total_to_delete == 0:
            return 0
        
        deleted_count = 0
        
        # Delete in batches to avoid long-running transactions
        while deleted_count < total_to_delete:
            # Get batch of old logs
            batch_query = select(AuditLog.id).where(
                AuditLog.event_timestamp < cutoff_date
            ).limit(batch_size)
            
            batch_result = await db.execute(batch_query)
            batch_ids = [row[0] for row in batch_result]
            
            if not batch_ids:
                break
            
            # Delete batch
            delete_query = select(AuditLog).where(AuditLog.id.in_(batch_ids))
            delete_result = await db.execute(delete_query)
            logs_to_delete = delete_result.scalars().all()
            
            for log in logs_to_delete:
                await db.delete(log)
            
            await db.commit()
            deleted_count += len(logs_to_delete)
        
        # Log the cleanup operation
        from core.gdpr_helpers import log_audit_event
        await log_audit_event(
            db=db,
            event_type=AuditEventType.RETENTION_POLICY_APPLIED,
            event_description=f"Audit log cleanup completed: {deleted_count} logs deleted",
            system_component="audit_log_crud",
            legal_basis="legal_obligation",
            processing_purpose="data_retention_compliance",
            risk_level="low",
            operation_details={
                "deleted_count": deleted_count,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat()
            }
        )
        
        return deleted_count
        
    except Exception as e:
        await db.rollback()
        from core.gdpr_helpers import log_audit_event
        await log_audit_event(
            db=db,
            event_type=AuditEventType.RETENTION_POLICY_APPLIED,
            event_description=f"Failed audit log cleanup: {str(e)}",
            system_component="audit_log_crud",
            risk_level="high"
        )
        raise


async def export_audit_logs(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    user_id: Optional[uuid.UUID] = None,
    requesting_user_id: Optional[uuid.UUID] = None,
    format: str = "json"
) -> List[Dict[str, Any]]:
    """Export audit logs for compliance reporting"""
    try:
        # Get logs for the specified period
        logs = await get_audit_logs(
            db=db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Large limit for export
            requesting_user_id=requesting_user_id
        )
        
        # Convert to export format
        export_data = []
        for log in logs:
            log_data = {
                "id": str(log.id),
                "event_type": log.event_type.value,
                "event_description": log.event_description,
                "event_timestamp": log.event_timestamp.isoformat(),
                "user_id": str(log.user_id) if log.user_id else None,
                "data_subject_id": str(log.data_subject_id) if log.data_subject_id else None,
                "invoice_id": str(log.invoice_id) if log.invoice_id else None,
                "system_component": log.system_component,
                "risk_level": log.risk_level,
                "legal_basis": log.legal_basis,
                "processing_purpose": log.processing_purpose,
                "data_categories_accessed": log.data_categories_accessed,
                "operation_details": log.operation_details,
                "compliance_notes": log.compliance_notes,
                "user_ip_address": log.user_ip_address,
                "user_agent": log.user_agent,
                "session_id": log.session_id
            }
            export_data.append(log_data)
        
        # Log the export operation
        if requesting_user_id:
            from core.gdpr_helpers import log_audit_event
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_EXPORT,
                event_description=f"Audit logs exported ({len(export_data)} records)",
                user_id=requesting_user_id,
                system_component="audit_log_crud",
                legal_basis="legal_obligation",
                processing_purpose="compliance_reporting",
                risk_level="medium",
                operation_details={
                    "export_count": len(export_data),
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "format": format
                }
            )
        
        return export_data
        
    except Exception as e:
        if requesting_user_id:
            from core.gdpr_helpers import log_audit_event
            await log_audit_event(
                db=db,
                event_type=AuditEventType.DATA_EXPORT,
                event_description=f"Failed audit logs export: {str(e)}",
                user_id=requesting_user_id,
                system_component="audit_log_crud",
                risk_level="high"
            )
        raise