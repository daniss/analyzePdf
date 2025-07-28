"""
Plan Comptable Général (French Chart of Accounts) Service

Professional-grade PCG mapping service for French accounting compliance.
Provides intelligent mapping from invoice descriptions to French account codes
with automatic fallbacks and expert-comptable ready functionality.

Key Features:
- Standard French accounting account codes (Classes 1-7)
- AI-powered intelligent mapping from descriptions to accounts
- Software-specific mappings (Sage, EBP, Ciel)
- Default account fallbacks for zero-decision workflow
- TVA account management (445662, 445663, etc.)
- Expert-comptable validation and compliance
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from models.french_compliance import PlanComptableGeneral
from schemas.invoice import LineItem, FrenchTVABreakdown

logger = logging.getLogger(__name__)


class PCGAccountCategory(Enum):
    """French accounting account categories (Classes 1-7)"""
    CAPITAUX = "capitaux"                    # Class 1 - Capital accounts
    IMMOBILISATIONS = "immobilisations"      # Class 2 - Fixed assets
    STOCKS = "stocks"                        # Class 3 - Inventory
    TIERS = "tiers"                         # Class 4 - Third parties
    FINANCIERS = "financiers"               # Class 5 - Financial accounts
    CHARGES = "charges"                     # Class 6 - Expenses
    PRODUITS = "produits"                   # Class 7 - Income


class TVAAccountType(Enum):
    """TVA account types for French accounting"""
    DEDUCTIBLE_BIENS = "deductible_biens"           # TVA déductible sur biens (20%)
    DEDUCTIBLE_SERVICES = "deductible_services"     # TVA déductible sur services (10%)
    DEDUCTIBLE_IMMOBILISATIONS = "deductible_immo"  # TVA déductible sur immobilisations
    DEDUCTIBLE_AUTRE = "deductible_autre"           # TVA déductible autres taux
    COLLECTEE_NORMALE = "collectee_normale"         # TVA collectée 20%
    COLLECTEE_REDUITE = "collectee_reduite"         # TVA collectée 10%
    COLLECTEE_SUPER_REDUITE = "collectee_super"     # TVA collectée 5.5%


@dataclass
class PCGMappingResult:
    """Result of PCG account mapping"""
    account_code: str
    account_name: str
    confidence_score: float  # 0.0 to 1.0
    mapping_source: str      # 'ai', 'keyword', 'default', 'manual'
    category: str
    subcategory: Optional[str] = None
    suggested_alternatives: List[str] = None


@dataclass
class PCGAccount:
    """French accounting account definition"""
    code: str
    name: str
    category: PCGAccountCategory
    subcategory: Optional[str]
    keywords: List[str]
    vat_applicable: bool
    default_vat_rate: Optional[float]
    sage_mapping: Optional[str] = None
    ebp_mapping: Optional[str] = None
    ciel_mapping: Optional[str] = None


class PlanComptableGeneralService:
    """
    Professional PCG (Plan Comptable Général) service for French accounting
    
    Provides intelligent mapping from invoice line items to French accounting codes
    with AI-powered description analysis and expert-comptable compliance.
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self._accounts_cache: Optional[Dict[str, PlanComptableGeneral]] = None
        self._keyword_mapping: Optional[Dict[str, List[str]]] = None
        
        # Load accounts into cache on initialization
        self._load_accounts_cache()
    
    def map_line_item_to_account(self, line_item: LineItem, use_ai: bool = True) -> PCGMappingResult:
        """
        Map an invoice line item to the most appropriate French accounting code
        
        Args:
            line_item: Invoice line item to map
            use_ai: Whether to use AI-powered mapping (fallback to keyword mapping if False)
            
        Returns:
            PCGMappingResult with account code and confidence score
        """
        logger.info(f"Mapping line item: {line_item.description[:50]}...")
        
        # First try exact keyword mapping (fastest and most reliable)
        keyword_result = self._map_by_keywords(line_item.description)
        if keyword_result and keyword_result.confidence_score >= 0.8:
            logger.info(f"High-confidence keyword mapping: {keyword_result.account_code}")
            return keyword_result
        
        # Try AI-powered mapping if enabled and keyword mapping has low confidence
        if use_ai:
            ai_result = self._map_by_ai_analysis(line_item)
            if ai_result and ai_result.confidence_score > (keyword_result.confidence_score if keyword_result else 0):
                logger.info(f"AI mapping preferred: {ai_result.account_code}")
                return ai_result
        
        # Use keyword result if available
        if keyword_result:
            logger.info(f"Using keyword mapping: {keyword_result.account_code}")
            return keyword_result
        
        # Fallback to default account based on line item characteristics
        default_result = self._get_default_account(line_item)
        logger.info(f"Using default account: {default_result.account_code}")
        return default_result
    
    def get_tva_account(self, tva_rate: float, is_deductible: bool = True) -> str:
        """
        Get appropriate TVA account code based on rate and type
        
        Args:
            tva_rate: TVA rate (20.0, 10.0, 5.5, 2.1, 0.0)
            is_deductible: True for TVA déductible, False for TVA collectée
            
        Returns:
            French TVA account code
        """
        if is_deductible:
            # TVA déductible accounts (Class 445)
            if tva_rate == 20.0:
                return "445662"  # TVA déductible sur biens 20%
            elif tva_rate == 10.0:
                return "445663"  # TVA déductible sur services 10%
            elif tva_rate in [5.5, 2.1]:
                return "445664"  # TVA déductible autres taux
            elif tva_rate == 0.0:
                return "445664"  # TVA déductible (exonéré)
            else:
                return "445662"  # Default to standard rate
        else:
            # TVA collectée accounts (Class 445)
            if tva_rate == 20.0:
                return "445711"  # TVA collectée 20%
            elif tva_rate == 10.0:
                return "445712"  # TVA collectée 10%
            elif tva_rate == 5.5:
                return "445713"  # TVA collectée 5.5%
            elif tva_rate == 2.1:
                return "445714"  # TVA collectée 2.1%
            else:
                return "445711"  # Default to standard rate
    
    def get_account_by_code(self, account_code: str) -> Optional[PlanComptableGeneral]:
        """Get account information by code"""
        if not self._accounts_cache:
            self._load_accounts_cache()
        
        return self._accounts_cache.get(account_code)
    
    def search_accounts(self, search_term: str, category: Optional[str] = None) -> List[PlanComptableGeneral]:
        """
        Search accounts by name, keywords, or description
        
        Args:
            search_term: Term to search for
            category: Optional category filter
            
        Returns:
            List of matching accounts
        """
        query = self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.is_active == True
        )
        
        # Add category filter if specified
        if category:
            query = query.filter(PlanComptableGeneral.account_category == category)
        
        # Search in account name and keywords
        search_filter = or_(
            PlanComptableGeneral.account_name.ilike(f'%{search_term}%'),
            func.json_array_length(
                func.json_extract(PlanComptableGeneral.keywords, f'$[*]')
            ) > 0
        )
        
        query = query.filter(search_filter)
        
        return query.limit(20).all()
    
    def get_accounts_by_category(self, category: PCGAccountCategory) -> List[PlanComptableGeneral]:
        """Get all accounts in a specific category"""
        return self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.account_category == category.value,
            PlanComptableGeneral.is_active == True
        ).order_by(PlanComptableGeneral.account_code).all()
    
    def get_software_mapping(self, account_code: str, software: str) -> Optional[str]:
        """
        Get account mapping for specific accounting software
        
        Args:
            account_code: PCG account code
            software: Software name ('sage', 'ebp', 'ciel')
            
        Returns:
            Software-specific account code or None
        """
        account = self.get_account_by_code(account_code)
        if not account:
            return None
        
        return account.get_mapping_for_software(software)
    
    def validate_account_code(self, account_code: str) -> bool:
        """Validate if account code exists and is active"""
        return account_code in (self._accounts_cache or {})
    
    def get_expense_categories(self) -> Dict[str, List[str]]:
        """Get organized expense account categories for UI selection"""
        categories = {
            "Services extérieurs": [],
            "Personnel extérieur": [],
            "Transports et déplacements": [],
            "Télécommunications": [],
            "Publicité et marketing": [],
            "Matériel et équipements": [],
            "Achats": [],
            "Autres charges": []
        }
        
        # Populate categories with actual account codes
        expense_accounts = self.get_accounts_by_category(PCGAccountCategory.CHARGES)
        
        for account in expense_accounts:
            code_prefix = account.account_code[:3]
            
            if code_prefix == "611":
                categories["Services extérieurs"].append(account.account_code)
            elif code_prefix == "621":
                categories["Personnel extérieur"].append(account.account_code)
            elif code_prefix in ["624", "625"]:
                categories["Transports et déplacements"].append(account.account_code)
            elif code_prefix == "626":
                categories["Télécommunications"].append(account.account_code)
            elif code_prefix == "623":
                categories["Publicité et marketing"].append(account.account_code)
            elif code_prefix in ["218", "606"]:
                categories["Matériel et équipements"].append(account.account_code)
            elif code_prefix in ["601", "607"]:
                categories["Achats"].append(account.account_code)
            else:
                categories["Autres charges"].append(account.account_code)
        
        return categories
    
    # ==========================================
    # PRIVATE METHODS
    # ==========================================
    
    def _load_accounts_cache(self):
        """Load all active accounts into memory cache"""
        try:
            accounts = self.db.query(PlanComptableGeneral).filter(
                PlanComptableGeneral.is_active == True
            ).all()
            
            self._accounts_cache = {account.account_code: account for account in accounts}
            self._build_keyword_mapping()
            
            logger.info(f"Loaded {len(self._accounts_cache)} PCG accounts into cache")
            
        except Exception as e:
            logger.error(f"Failed to load PCG accounts cache: {e}")
            self._accounts_cache = {}
            self._keyword_mapping = {}
    
    def _build_keyword_mapping(self):
        """Build keyword to account code mapping for fast lookup"""
        self._keyword_mapping = {}
        
        for account in self._accounts_cache.values():
            if account.keywords:
                for keyword in account.keywords:
                    keyword_lower = keyword.lower().strip()
                    if keyword_lower not in self._keyword_mapping:
                        self._keyword_mapping[keyword_lower] = []
                    self._keyword_mapping[keyword_lower].append(account.account_code)
    
    def _map_by_keywords(self, description: str) -> Optional[PCGMappingResult]:
        """
        Map description to account using keyword matching
        
        Args:
            description: Item description to analyze
            
        Returns:
            PCGMappingResult or None if no match found
        """
        if not description or not self._keyword_mapping:
            return None
        
        description_lower = description.lower()
        best_match = None
        best_score = 0.0
        
        # Check each keyword for matches
        for keyword, account_codes in self._keyword_mapping.items():
            if keyword in description_lower:
                # Calculate match score based on keyword length and frequency
                keyword_score = len(keyword) / len(description_lower)
                keyword_score = min(keyword_score * 2, 1.0)  # Boost score but cap at 1.0
                
                if keyword_score > best_score:
                    # Use first account code (should be most relevant)
                    account_code = account_codes[0]
                    account = self._accounts_cache.get(account_code)
                    
                    if account:
                        best_match = PCGMappingResult(
                            account_code=account.account_code,
                            account_name=account.account_name,
                            confidence_score=keyword_score,
                            mapping_source='keyword',
                            category=account.account_category,
                            subcategory=account.account_subcategory,
                            suggested_alternatives=account_codes[1:3] if len(account_codes) > 1 else []
                        )
                        best_score = keyword_score
        
        return best_match
    
    def _map_by_ai_analysis(self, line_item: LineItem) -> Optional[PCGMappingResult]:
        """
        Use AI to analyze line item and suggest account code
        
        This is a placeholder for AI integration. In the MVP, we'll use enhanced
        keyword matching with semantic analysis.
        
        Args:
            line_item: Line item to analyze
            
        Returns:
            PCGMappingResult or None
        """
        # For MVP, use enhanced keyword analysis instead of full AI
        # This provides good results without external AI dependency
        
        description = line_item.description.lower()
        
        # Enhanced semantic keyword matching
        semantic_mappings = {
            # Services extérieurs (611000)
            ('service', 'prestation', 'consultation', 'conseil', 'formation', 
             'assistance', 'maintenance', 'support', 'audit', 'expertise'): "611000",
            
            # Personnel extérieur (621000)
            ('intérim', 'freelance', 'consultant', 'sous-traitance', 'mission',
             'externe', 'temporaire', 'vacation'): "621000",
            
            # Transports (624100)
            ('transport', 'livraison', 'expédition', 'fret', 'logistique',
             'déplacement', 'voyage', 'carburant', 'essence', 'gazole'): "624100",
            
            # Télécommunications (626000)
            ('téléphone', 'internet', 'télécommunication', 'ligne', 'forfait',
             'communication', 'web', 'hébergement', 'domaine', 'mobile'): "626000",
            
            # Publicité (623000)
            ('publicité', 'marketing', 'communication', 'impression', 'affichage',
             'promotion', 'advertising', 'design', 'graphique', 'site'): "623000",
            
            # Matériel informatique (613000)
            ('ordinateur', 'informatique', 'logiciel', 'matériel', 'hardware',
             'software', 'licence', 'équipement', 'machine', 'serveur'): "613000",
        }
        
        for keywords, account_code in semantic_mappings.items():
            for keyword in keywords:
                if keyword in description:
                    account = self._accounts_cache.get(account_code)
                    if account:
                        # Calculate confidence based on keyword relevance and line item amount
                        confidence = 0.7  # AI mapping gets medium confidence
                        
                        # Boost confidence for exact matches
                        if description.startswith(keyword) or description.endswith(keyword):
                            confidence = 0.85
                        
                        return PCGMappingResult(
                            account_code=account.account_code,
                            account_name=account.account_name,
                            confidence_score=confidence,
                            mapping_source='ai',
                            category=account.account_category,
                            subcategory=account.account_subcategory
                        )
        
        return None
    
    def _get_default_account(self, line_item: LineItem) -> PCGMappingResult:
        """
        Get default account when no specific mapping found
        
        Args:
            line_item: Line item for context
            
        Returns:
            PCGMappingResult with default account
        """
        # Default to general purchases account
        default_code = "607000"  # Achats de marchandises
        
        # Use amount-based heuristics for better defaults
        if line_item.total > 1000:
            # Large amounts might be equipment/investments
            default_code = "218300"  # Matériel informatique
        elif line_item.total < 50:
            # Small amounts might be supplies
            default_code = "606000"  # Autres approvisionnements
        
        account = self._accounts_cache.get(default_code)
        if not account:
            # Fallback to first available account
            account = next(iter(self._accounts_cache.values()))
            default_code = account.account_code
        
        return PCGMappingResult(
            account_code=default_code,
            account_name=account.account_name if account else "Compte par défaut",
            confidence_score=0.3,  # Low confidence for default mapping
            mapping_source='default',
            category=account.account_category if account else "charges",
            subcategory=account.account_subcategory if account else None
        )


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def get_pcg_service(db_session: Session) -> PlanComptableGeneralService:
    """Factory function to get PCG service instance"""
    return PlanComptableGeneralService(db_session)


def map_invoice_line_items(line_items: List[LineItem], db_session: Session) -> List[PCGMappingResult]:
    """
    Convenience function to map multiple line items to PCG accounts
    
    Args:
        line_items: List of invoice line items
        db_session: Database session
        
    Returns:
        List of PCG mapping results
    """
    pcg_service = get_pcg_service(db_session)
    return [pcg_service.map_line_item_to_account(item) for item in line_items]


# ==========================================
# VALIDATION UTILITIES
# ==========================================

def validate_pcg_mapping(mapping_result: PCGMappingResult, min_confidence: float = 0.5) -> bool:
    """
    Validate PCG mapping result meets minimum confidence requirements
    
    Args:
        mapping_result: PCG mapping result to validate
        min_confidence: Minimum confidence score (0.0 to 1.0)
        
    Returns:
        True if mapping meets requirements
    """
    return (mapping_result.confidence_score >= min_confidence and
            mapping_result.account_code and
            len(mapping_result.account_code) >= 6)


def get_pcg_account_class(account_code: str) -> int:
    """
    Get French accounting class (1-7) from account code
    
    Args:
        account_code: PCG account code
        
    Returns:
        Account class number (1-7)
    """
    if not account_code or len(account_code) < 1:
        return 0
    
    try:
        return int(account_code[0])
    except (ValueError, IndexError):
        return 0