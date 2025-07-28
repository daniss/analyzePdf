"""
Manual Review Queue System

This module manages corrections that require manual review by expert-comptables.
It provides a queue system for uncertain auto-corrections, allowing experts to
review, approve, or reject suggestions while maintaining complete audit trails.

Features:
- Queue management for uncertain corrections
- Expert review interface
- Approval/rejection workflow
- Learning from expert decisions
- Priority-based queue processing
- Real-time notifications
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey, UUID, Numeric, Integer
from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import relationship

from core.database import Base
from core.auto_correction.auto_correction_engine import (
    CorrectionSuggestion, CorrectionDecision, CorrectionStatus, 
    CorrectionConfidence, CorrectionAction
)
from core.gdpr_audit import log_audit_event

logger = logging.getLogger(__name__)

class ReviewPriority(str, Enum):
    """Priority levels for manual review"""
    URGENT = "urgent"       # Critical fields, export blocking
    HIGH = "high"           # Important fields, compliance issues
    MEDIUM = "medium"       # Standard corrections
    LOW = "low"             # Nice-to-have improvements

class ReviewStatus(str, Enum):
    """Status of review items"""
    PENDING = "pending"         # Awaiting review
    IN_REVIEW = "in_review"     # Being reviewed by expert
    APPROVED = "approved"       # Approved by expert
    REJECTED = "rejected"       # Rejected by expert
    APPLIED = "applied"         # Approved and applied to invoice
    EXPIRED = "expired"         # Review expired (too old)

class ExpertAction(str, Enum):
    """Actions taken by expert reviewers"""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"          # Approve with modifications
    DELEGATE = "delegate"      # Assign to another expert
    REQUEST_INFO = "request_info"  # Request more information

class ManualReviewItem(Base):
    """
    Manual review queue item for uncertain corrections
    """
    __tablename__ = "manual_review_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    
    # Correction details
    field_name = Column(String(100), nullable=False)
    original_value = Column(Text, nullable=True)
    suggested_value = Column(Text, nullable=False)
    correction_action = Column(String(50), nullable=False)  # CorrectionAction
    
    # Confidence and reasoning
    confidence_score = Column(Numeric(5, 4), nullable=False)  # 0.0000 to 1.0000
    confidence_level = Column(String(20), nullable=False)     # CorrectionConfidence
    reasoning = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)
    
    # Review status
    review_status = Column(String(20), nullable=False, default=ReviewStatus.PENDING.value)
    review_priority = Column(String(20), nullable=False, default=ReviewPriority.MEDIUM.value)
    
    # Assignment and review
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expert_action = Column(String(20), nullable=True)  # ExpertAction
    expert_notes = Column(Text, nullable=True)
    
    # Modified suggestion (if expert changed the suggestion)
    modified_value = Column(Text, nullable=True)
    modified_reasoning = Column(Text, nullable=True)
    
    # Timing and deadlines
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    review_started_at = Column(DateTime(timezone=True), nullable=True)
    
    # Learning and feedback
    expert_confidence = Column(Numeric(5, 4), nullable=True)  # Expert's confidence in their decision
    correction_applied = Column(Boolean, nullable=False, default=False)
    application_successful = Column(Boolean, nullable=True)
    
    # Cost tracking
    estimated_cost = Column(Numeric(10, 4), nullable=True)
    actual_cost = Column(Numeric(10, 4), nullable=True)
    time_spent_minutes = Column(Integer, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "invoice_id": str(self.invoice_id),
            "field_name": self.field_name,
            "original_value": self.original_value,
            "suggested_value": self.suggested_value,
            "correction_action": self.correction_action,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "confidence_level": self.confidence_level,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "review_status": self.review_status,
            "review_priority": self.review_priority,
            "assigned_to": str(self.assigned_to) if self.assigned_to else None,
            "reviewed_by": str(self.reviewed_by) if self.reviewed_by else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "expert_action": self.expert_action,
            "expert_notes": self.expert_notes,
            "modified_value": self.modified_value,
            "modified_reasoning": self.modified_reasoning,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "expert_confidence": float(self.expert_confidence) if self.expert_confidence else None,
            "correction_applied": self.correction_applied,
            "estimated_cost": float(self.estimated_cost) if self.estimated_cost else None,
            "time_spent_minutes": self.time_spent_minutes
        }

class ExpertReviewStats(Base):
    """
    Statistics for expert reviewers to track performance and learning
    """
    __tablename__ = "expert_review_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    expert_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Review performance
    total_reviews = Column(Integer, nullable=False, default=0)
    approvals = Column(Integer, nullable=False, default=0)
    rejections = Column(Integer, nullable=False, default=0)
    modifications = Column(Integer, nullable=False, default=0)
    
    # Accuracy metrics
    correct_decisions = Column(Integer, nullable=False, default=0)
    incorrect_decisions = Column(Integer, nullable=False, default=0)
    accuracy_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    
    # Time metrics
    average_review_time_minutes = Column(Numeric(8, 2), nullable=True)
    total_time_spent_minutes = Column(Integer, nullable=False, default=0)
    
    # Specialization areas
    field_expertise = Column(JSON, nullable=True)  # Field names and accuracy rates
    correction_type_expertise = Column(JSON, nullable=True)  # Correction types and accuracy
    
    # Period tracking
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ManualReviewQueueManager:
    """
    Manages the manual review queue for uncertain corrections
    """
    
    # Review expiration times by priority
    EXPIRATION_TIMES = {
        ReviewPriority.URGENT: timedelta(hours=2),
        ReviewPriority.HIGH: timedelta(hours=24),
        ReviewPriority.MEDIUM: timedelta(days=3),
        ReviewPriority.LOW: timedelta(weeks=1)
    }
    
    def __init__(self):
        self.notification_callbacks = []
    
    async def queue_correction_for_review(
        self,
        correction_decision: CorrectionDecision,
        invoice_id: str,
        db_session: AsyncSession,
        user_id: Optional[str] = None,
        priority: Optional[ReviewPriority] = None
    ) -> ManualReviewItem:
        """
        Add a correction to the manual review queue
        
        Args:
            correction_decision: Correction decision to review
            invoice_id: Invoice ID
            db_session: Database session
            user_id: User who triggered the correction
            priority: Review priority (auto-determined if not provided)
            
        Returns:
            Created review item
        """
        
        suggestion = correction_decision.suggestion
        
        # Determine priority if not provided
        if not priority:
            priority = self._determine_priority(suggestion, correction_decision)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + self.EXPIRATION_TIMES[priority]
        
        # Create review item
        review_item = ManualReviewItem(
            invoice_id=uuid.UUID(invoice_id),
            field_name=suggestion.field_name,
            original_value=str(suggestion.original_value) if suggestion.original_value else None,
            suggested_value=str(suggestion.corrected_value),
            correction_action=suggestion.correction_action.value,
            confidence_score=suggestion.confidence,
            confidence_level=correction_decision.confidence_level.value,
            reasoning=suggestion.reasoning,
            evidence=suggestion.evidence,
            review_priority=priority.value,
            expires_at=expires_at,
            estimated_cost=suggestion.cost_estimate
        )
        
        db_session.add(review_item)
        await db_session.commit()
        
        # Log audit event
        await log_audit_event(
            db_session,
            user_id=user_id,
            operation_type="correction_queued_for_manual_review",
            data_categories=["correction_queue", "manual_review", "expert_review"],
            risk_level="low",
            details={
                "review_item_id": str(review_item.id),
                "invoice_id": invoice_id,
                "field_name": suggestion.field_name,
                "confidence": suggestion.confidence,
                "priority": priority.value,
                "expires_at": expires_at.isoformat()
            }
        )
        
        # Send notifications
        await self._notify_experts(review_item, db_session)
        
        logger.info(f"Queued correction for manual review: {suggestion.field_name} (priority: {priority.value})")
        
        return review_item
    
    async def assign_review_to_expert(
        self,
        review_item_id: str,
        expert_id: str,
        db_session: AsyncSession,
        assigned_by: Optional[str] = None
    ) -> bool:
        """
        Assign a review item to a specific expert
        
        Args:
            review_item_id: Review item ID
            expert_id: Expert user ID
            db_session: Database session
            assigned_by: User who made the assignment
            
        Returns:
            True if assignment successful
        """
        
        try:
            stmt = update(ManualReviewItem).where(
                ManualReviewItem.id == uuid.UUID(review_item_id),
                ManualReviewItem.review_status == ReviewStatus.PENDING.value
            ).values(
                assigned_to=uuid.UUID(expert_id),
                review_status=ReviewStatus.IN_REVIEW.value,
                review_started_at=datetime.utcnow()
            )
            
            result = await db_session.execute(stmt)
            await db_session.commit()
            
            if result.rowcount > 0:
                await log_audit_event(
                    db_session,
                    user_id=assigned_by,
                    operation_type="review_item_assigned",
                    data_categories=["assignment", "expert_review"],
                    risk_level="low",
                    details={
                        "review_item_id": review_item_id,
                        "expert_id": expert_id,
                        "assigned_by": assigned_by
                    }
                )
                
                logger.info(f"Assigned review item {review_item_id} to expert {expert_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error assigning review to expert: {e}")
            await db_session.rollback()
            return False
    
    async def submit_expert_review(
        self,
        review_item_id: str,
        expert_id: str,
        action: ExpertAction,
        expert_notes: Optional[str] = None,
        modified_value: Optional[str] = None,
        modified_reasoning: Optional[str] = None,
        expert_confidence: Optional[float] = None,
        time_spent_minutes: Optional[int] = None,
        db_session: AsyncSession = None
    ) -> bool:
        """
        Submit expert review decision
        
        Args:
            review_item_id: Review item ID
            expert_id: Expert user ID
            action: Expert action taken
            expert_notes: Expert's notes
            modified_value: Modified correction value (if action is MODIFY)
            modified_reasoning: Modified reasoning (if action is MODIFY)
            expert_confidence: Expert's confidence in their decision
            time_spent_minutes: Time spent on review
            db_session: Database session
            
        Returns:
            True if review submitted successfully
        """
        
        try:
            # Map expert action to review status
            status_mapping = {
                ExpertAction.APPROVE: ReviewStatus.APPROVED,
                ExpertAction.REJECT: ReviewStatus.REJECTED,
                ExpertAction.MODIFY: ReviewStatus.APPROVED,  # Modified approval
                ExpertAction.REQUEST_INFO: ReviewStatus.PENDING,  # Back to pending
                ExpertAction.DELEGATE: ReviewStatus.PENDING  # Reassign
            }
            
            new_status = status_mapping[action]
            
            stmt = update(ManualReviewItem).where(
                ManualReviewItem.id == uuid.UUID(review_item_id),
                ManualReviewItem.assigned_to == uuid.UUID(expert_id)
            ).values(
                review_status=new_status.value,
                reviewed_by=uuid.UUID(expert_id),
                reviewed_at=datetime.utcnow(),
                expert_action=action.value,
                expert_notes=expert_notes,
                modified_value=modified_value,
                modified_reasoning=modified_reasoning,
                expert_confidence=expert_confidence,
                time_spent_minutes=time_spent_minutes
            )
            
            result = await db_session.execute(stmt)
            await db_session.commit()
            
            if result.rowcount > 0:
                # Update expert statistics
                await self._update_expert_stats(expert_id, action, time_spent_minutes, db_session)
                
                # Log audit event
                await log_audit_event(
                    db_session,
                    user_id=expert_id,
                    operation_type="expert_review_submitted",
                    data_categories=["expert_review", "decision_making"],
                    risk_level="low",
                    details={
                        "review_item_id": review_item_id,
                        "expert_id": expert_id,
                        "action": action.value,
                        "confidence": expert_confidence,
                        "time_spent": time_spent_minutes,
                        "has_modifications": modified_value is not None
                    }
                )
                
                # If approved, trigger application
                if new_status == ReviewStatus.APPROVED:
                    await self._trigger_correction_application(review_item_id, db_session)
                
                logger.info(f"Expert review submitted for item {review_item_id}: {action.value}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error submitting expert review: {e}")
            await db_session.rollback()
            return False
    
    async def get_pending_reviews(
        self,
        expert_id: Optional[str] = None,
        priority: Optional[ReviewPriority] = None,
        limit: int = 50,
        db_session: AsyncSession = None
    ) -> List[ManualReviewItem]:
        """
        Get pending review items
        
        Args:
            expert_id: Filter by assigned expert
            priority: Filter by priority
            limit: Maximum number of items
            db_session: Database session
            
        Returns:
            List of pending review items
        """
        
        query = select(ManualReviewItem).where(
            or_(
                ManualReviewItem.review_status == ReviewStatus.PENDING.value,
                ManualReviewItem.review_status == ReviewStatus.IN_REVIEW.value
            )
        )
        
        if expert_id:
            query = query.where(ManualReviewItem.assigned_to == uuid.UUID(expert_id))
        
        if priority:
            query = query.where(ManualReviewItem.review_priority == priority.value)
        
        # Order by priority and creation time
        priority_order = func.case(
            (ManualReviewItem.review_priority == ReviewPriority.URGENT.value, 1),
            (ManualReviewItem.review_priority == ReviewPriority.HIGH.value, 2),
            (ManualReviewItem.review_priority == ReviewPriority.MEDIUM.value, 3),
            (ManualReviewItem.review_priority == ReviewPriority.LOW.value, 4),
            else_=5
        )
        
        query = query.order_by(priority_order, ManualReviewItem.created_at).limit(limit)
        
        result = await db_session.execute(query)
        return result.scalars().all()
    
    async def get_expert_queue(
        self,
        expert_id: str,
        include_completed: bool = False,
        db_session: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get expert's review queue with statistics
        
        Args:
            expert_id: Expert user ID
            include_completed: Include completed reviews
            db_session: Database session
            
        Returns:
            Expert queue data with statistics
        """
        
        # Get pending items assigned to expert
        pending_query = select(ManualReviewItem).where(
            ManualReviewItem.assigned_to == uuid.UUID(expert_id),
            or_(
                ManualReviewItem.review_status == ReviewStatus.PENDING.value,
                ManualReviewItem.review_status == ReviewStatus.IN_REVIEW.value
            )
        ).order_by(ManualReviewItem.created_at)
        
        pending_result = await db_session.execute(pending_query)
        pending_items = pending_result.scalars().all()
        
        # Get completed items if requested
        completed_items = []
        if include_completed:
            completed_query = select(ManualReviewItem).where(
                ManualReviewItem.reviewed_by == uuid.UUID(expert_id),
                or_(
                    ManualReviewItem.review_status == ReviewStatus.APPROVED.value,
                    ManualReviewItem.review_status == ReviewStatus.REJECTED.value
                )
            ).order_by(desc(ManualReviewItem.reviewed_at)).limit(20)
            
            completed_result = await db_session.execute(completed_query)
            completed_items = completed_result.scalars().all()
        
        # Get expert statistics
        stats_query = select(ExpertReviewStats).where(
            ExpertReviewStats.expert_id == uuid.UUID(expert_id)
        ).order_by(desc(ExpertReviewStats.last_updated)).limit(1)
        
        stats_result = await db_session.execute(stats_query)
        stats = stats_result.scalar_one_or_none()
        
        return {
            "expert_id": expert_id,
            "pending_items": [item.to_dict() for item in pending_items],
            "completed_items": [item.to_dict() for item in completed_items] if include_completed else [],
            "queue_stats": {
                "pending_count": len(pending_items),
                "urgent_count": len([i for i in pending_items if i.review_priority == ReviewPriority.URGENT.value]),
                "high_count": len([i for i in pending_items if i.review_priority == ReviewPriority.HIGH.value]),
                "medium_count": len([i for i in pending_items if i.review_priority == ReviewPriority.MEDIUM.value]),
                "low_count": len([i for i in pending_items if i.review_priority == ReviewPriority.LOW.value])
            },
            "expert_stats": {
                "total_reviews": stats.total_reviews if stats else 0,
                "accuracy_rate": float(stats.accuracy_rate) if stats and stats.accuracy_rate else None,
                "average_review_time": float(stats.average_review_time_minutes) if stats and stats.average_review_time_minutes else None,
                "approvals": stats.approvals if stats else 0,
                "rejections": stats.rejections if stats else 0,
                "modifications": stats.modifications if stats else 0
            }
        }
    
    async def expire_old_reviews(self, db_session: AsyncSession) -> int:
        """
        Mark expired review items as expired
        
        Args:
            db_session: Database session
            
        Returns:
            Number of items expired
        """
        
        try:
            stmt = update(ManualReviewItem).where(
                ManualReviewItem.review_status == ReviewStatus.PENDING.value,
                ManualReviewItem.expires_at < datetime.utcnow()
            ).values(
                review_status=ReviewStatus.EXPIRED.value
            )
            
            result = await db_session.execute(stmt)
            await db_session.commit()
            
            expired_count = result.rowcount
            
            if expired_count > 0:
                logger.info(f"Expired {expired_count} old review items")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Error expiring old reviews: {e}")
            await db_session.rollback()
            return 0
    
    def _determine_priority(
        self,
        suggestion: CorrectionSuggestion,
        decision: CorrectionDecision
    ) -> ReviewPriority:
        """Determine review priority based on suggestion characteristics"""
        
        # Critical fields get higher priority
        critical_fields = ['siren_number', 'siret_number', 'total_ttc', 'invoice_number']
        if suggestion.field_name in critical_fields:
            if suggestion.confidence < 0.7:
                return ReviewPriority.URGENT
            else:
                return ReviewPriority.HIGH
        
        # High-value corrections get higher priority
        if suggestion.cost_estimate and suggestion.cost_estimate > 1.0:
            return ReviewPriority.HIGH
        
        # External validation required
        if suggestion.requires_external_validation:
            return ReviewPriority.HIGH
        
        # Based on confidence level
        if decision.confidence_level == CorrectionConfidence.MEDIUM:
            return ReviewPriority.MEDIUM
        elif decision.confidence_level == CorrectionConfidence.LOW:
            return ReviewPriority.HIGH
        else:
            return ReviewPriority.LOW
    
    async def _notify_experts(
        self,
        review_item: ManualReviewItem,
        db_session: AsyncSession
    ):
        """Send notifications to appropriate experts"""
        
        # This is a placeholder for notification system
        # In production, you'd integrate with email, Slack, or in-app notifications
        
        for callback in self.notification_callbacks:
            try:
                await callback(review_item)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")
    
    async def _update_expert_stats(
        self,
        expert_id: str,
        action: ExpertAction,
        time_spent: Optional[int],
        db_session: AsyncSession
    ):
        """Update expert review statistics"""
        
        try:
            # Get or create stats record
            stats_query = select(ExpertReviewStats).where(
                ExpertReviewStats.expert_id == uuid.UUID(expert_id),
                ExpertReviewStats.period_end.is_(None)  # Current period
            )
            
            result = await db_session.execute(stats_query)
            stats = result.scalar_one_or_none()
            
            if not stats:
                stats = ExpertReviewStats(
                    expert_id=uuid.UUID(expert_id),
                    period_start=datetime.utcnow()
                )
                db_session.add(stats)
            
            # Update counts
            stats.total_reviews += 1
            if action == ExpertAction.APPROVE:
                stats.approvals += 1
            elif action == ExpertAction.REJECT:
                stats.rejections += 1
            elif action == ExpertAction.MODIFY:
                stats.modifications += 1
            
            # Update time tracking
            if time_spent:
                stats.total_time_spent_minutes += time_spent
                if stats.total_reviews > 0:
                    stats.average_review_time_minutes = stats.total_time_spent_minutes / stats.total_reviews
            
            await db_session.commit()
            
        except Exception as e:
            logger.error(f"Error updating expert stats: {e}")
            await db_session.rollback()
    
    async def _trigger_correction_application(
        self,
        review_item_id: str,
        db_session: AsyncSession
    ):
        """Trigger application of approved correction"""
        
        # This would integrate with the correction application system
        # For now, just mark as ready for application
        
        try:
            stmt = update(ManualReviewItem).where(
                ManualReviewItem.id == uuid.UUID(review_item_id)
            ).values(
                correction_applied=True
            )
            
            await db_session.execute(stmt)
            await db_session.commit()
            
            logger.info(f"Marked correction {review_item_id} for application")
            
        except Exception as e:
            logger.error(f"Error marking correction for application: {e}")
            await db_session.rollback()

# Convenience functions

async def queue_correction_for_review(
    correction_decision: CorrectionDecision,
    invoice_id: str,
    db_session: AsyncSession,
    user_id: Optional[str] = None,
    priority: Optional[ReviewPriority] = None
) -> ManualReviewItem:
    """Queue a correction for manual review"""
    manager = ManualReviewQueueManager()
    return await manager.queue_correction_for_review(
        correction_decision, invoice_id, db_session, user_id, priority
    )

async def get_expert_review_queue(
    expert_id: str,
    db_session: AsyncSession,
    include_completed: bool = False
) -> Dict[str, Any]:
    """Get expert's review queue"""
    manager = ManualReviewQueueManager()
    return await manager.get_expert_queue(expert_id, include_completed, db_session)