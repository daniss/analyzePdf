"""
French Compliance Validation Module

This module provides comprehensive French invoice compliance validation,
including SIREN/SIRET validation, TVA compliance, and regulatory checks.
"""

from .insee_client import (
    INSEEAPIClient,
    INSEECache,
    INSEECompanyInfo,
    INSEEEstablishmentInfo,
    validate_french_company,
    validate_french_establishment
)

__all__ = [
    "INSEEAPIClient",
    "INSEECache", 
    "INSEECompanyInfo",
    "INSEEEstablishmentInfo",
    "validate_french_company",
    "validate_french_establishment"
]