"""
Plan Comptable Général (French Chart of Accounts) Module

This module provides comprehensive Plan Comptable Général functionality
for French accounting compliance and expert-comptable requirements.

Components:
- pcg_service: Core service for intelligent account mapping
- standard_accounts: Standard French account definitions and data
- init_pcg: Initialization utilities for database setup

Key Features:
- AI-powered mapping from invoice descriptions to French account codes
- Standard French accounting codes (Classes 1-7)
- Software-specific mappings (Sage, EBP, Ciel)
- Expert-comptable compliance and validation
- Zero-decision workflow for invoice processing

Usage:
    from core.pcg import get_pcg_service, PCGMappingResult
    from core.pcg.standard_accounts import get_standard_pcg_accounts
    from core.pcg.init_pcg import PCGInitializer
"""

from .pcg_service import (
    PlanComptableGeneralService,
    PCGMappingResult, 
    PCGAccountCategory,
    TVAAccountType,
    get_pcg_service,
    map_invoice_line_items,
    validate_pcg_mapping,
    get_pcg_account_class
)

from .standard_accounts import (
    get_standard_pcg_accounts,
    get_essential_pcg_accounts,
    get_tva_mapping_by_rate,
    get_category_account_mapping,
    FRENCH_TVA_RATES
)

from .init_pcg import (
    PCGInitializer,
    initialize_pcg_essential,
    initialize_pcg_full,
    check_pcg_status
)

__all__ = [
    # Core service
    "PlanComptableGeneralService",
    "PCGMappingResult",
    "PCGAccountCategory", 
    "TVAAccountType",
    "get_pcg_service",
    "map_invoice_line_items",
    "validate_pcg_mapping",
    "get_pcg_account_class",
    
    # Standard accounts
    "get_standard_pcg_accounts",
    "get_essential_pcg_accounts", 
    "get_tva_mapping_by_rate",
    "get_category_account_mapping",
    "FRENCH_TVA_RATES",
    
    # Initialization
    "PCGInitializer",
    "initialize_pcg_essential",
    "initialize_pcg_full", 
    "check_pcg_status"
]

__version__ = "1.0.0"
__author__ = "InvoiceAI Team"
__description__ = "Plan Comptable Général module for French accounting compliance"