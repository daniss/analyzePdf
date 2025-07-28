"""
Auto-Correction Module

Intelligent error recovery and auto-correction system for French invoice compliance.
Enables zero-decision workflow for expert-comptables through automated error fixing
with confidence-based decisions and manual review queue for uncertain corrections.

Key Components:
- Auto-correction engine with specialized correctors
- Manual review queue for expert oversight
- Correction orchestrator for workflow integration
- Complete audit trail and performance tracking

Usage:
    from core.auto_correction import validate_and_auto_correct, zero_decision_validation
    
    # Validate with auto-correction
    result = await validate_and_auto_correct(invoice, db, user_id)
    
    # Zero-decision workflow
    result = await zero_decision_validation(invoice, db, user_id)
"""

from .auto_correction_engine import (
    IntelligentAutoCorrectionEngine,
    SIRENSIRETCorrector,
    TVACorrector,
    DateCorrector,
    AmountCorrector,
    CorrectionSuggestion,
    CorrectionDecision,
    CorrectionAction,
    CorrectionStatus,
    CorrectionConfidence,
    AutoCorrectionResult,
    auto_correct_invoice,
    get_correction_suggestions_only
)

from .manual_review_queue import (
    ManualReviewQueueManager,
    ManualReviewItem,
    ExpertReviewStats,
    ReviewPriority,
    ReviewStatus,
    ExpertAction,
    queue_correction_for_review,
    get_expert_review_queue
)

from .correction_orchestrator import (
    AutoCorrectionOrchestrator,
    CorrectionSettings,
    CorrectionMode,
    CorrectionTiming,
    EnhancedValidationResult,
    validate_and_auto_correct,
    zero_decision_validation
)

__all__ = [
    # Main orchestrator functions
    "validate_and_auto_correct",
    "zero_decision_validation",
    
    # Auto-correction engine
    "IntelligentAutoCorrectionEngine",
    "SIRENSIRETCorrector",
    "TVACorrector", 
    "DateCorrector",
    "AmountCorrector",
    "auto_correct_invoice",
    "get_correction_suggestions_only",
    
    # Manual review queue
    "ManualReviewQueueManager",
    "queue_correction_for_review",
    "get_expert_review_queue",
    
    # Orchestrator classes
    "AutoCorrectionOrchestrator",
    
    # Data models
    "CorrectionSuggestion",
    "CorrectionDecision",
    "AutoCorrectionResult",
    "EnhancedValidationResult",
    "ManualReviewItem",
    "ExpertReviewStats",
    "CorrectionSettings",
    
    # Enums
    "CorrectionAction",
    "CorrectionStatus", 
    "CorrectionConfidence",
    "CorrectionMode",
    "CorrectionTiming",
    "ReviewPriority",
    "ReviewStatus",
    "ExpertAction"
]

# Version info
__version__ = "1.0.0"
__author__ = "InvoiceAI Team"
__description__ = "Intelligent auto-correction system for French invoice compliance"