"""
API Routes for Plan Comptable Général (French Chart of Accounts) Management

Professional-grade endpoints for expert-comptables to manage and lookup
French accounting codes with intelligent mapping and compliance features.

Endpoints:
- GET /api/pcg/accounts - List and search PCG accounts
- GET /api/pcg/accounts/{account_code} - Get specific account details
- POST /api/pcg/accounts - Create new PCG account (admin only)
- PUT /api/pcg/accounts/{account_id} - Update PCG account (admin only)
- DELETE /api/pcg/accounts/{account_id} - Delete PCG account (admin only)
- POST /api/pcg/map-description - Map description to account code
- GET /api/pcg/categories - Get account categories for UI
- GET /api/pcg/tva-accounts - Get TVA-specific accounts
- GET /api/pcg/statistics - Get PCG usage statistics
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from core.database import get_db
from crud.pcg import PCGAccountCRUD, get_pcg_crud
from core.pcg.pcg_service import PlanComptableGeneralService, PCGMappingResult, get_pcg_service
from core.pcg.standard_accounts import get_category_account_mapping, get_tva_mapping_by_rate
from models.french_compliance import PlanComptableGeneral
from schemas.invoice import LineItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pcg", tags=["Plan Comptable Général"])


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class PCGAccountCreate(BaseModel):
    """Schema for creating a new PCG account"""
    account_code: str = Field(..., min_length=3, max_length=10, description="French account code (3-10 digits)")
    account_name: str = Field(..., min_length=1, max_length=200, description="Account name in French")
    account_category: str = Field(..., description="Account category (charges, produits, etc.)")
    account_subcategory: Optional[str] = Field(None, max_length=100, description="Account subcategory")
    vat_applicable: bool = Field(True, description="Whether VAT applies to this account")
    default_vat_rate: Optional[float] = Field(None, ge=0, le=100, description="Default VAT rate (%)")
    keywords: List[str] = Field(default_factory=list, description="Keywords for automatic mapping")
    sage_mapping: Optional[str] = Field(None, max_length=20, description="Sage account code mapping")
    ebp_mapping: Optional[str] = Field(None, max_length=20, description="EBP account code mapping")
    ciel_mapping: Optional[str] = Field(None, max_length=20, description="Ciel account code mapping")


class PCGAccountUpdate(BaseModel):
    """Schema for updating a PCG account"""
    account_name: Optional[str] = Field(None, min_length=1, max_length=200)
    account_category: Optional[str] = None
    account_subcategory: Optional[str] = Field(None, max_length=100)
    vat_applicable: Optional[bool] = None
    default_vat_rate: Optional[float] = Field(None, ge=0, le=100)
    keywords: Optional[List[str]] = None
    sage_mapping: Optional[str] = Field(None, max_length=20)
    ebp_mapping: Optional[str] = Field(None, max_length=20)
    ciel_mapping: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class PCGAccountResponse(BaseModel):
    """Schema for PCG account response"""
    id: UUID
    account_code: str
    account_name: str
    account_category: str
    account_subcategory: Optional[str]
    vat_applicable: bool
    default_vat_rate: Optional[float]
    keywords: List[str]
    sage_mapping: Optional[str]
    ebp_mapping: Optional[str]
    ciel_mapping: Optional[str]
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class DescriptionMappingRequest(BaseModel):
    """Schema for mapping description to account code"""
    description: str = Field(..., min_length=1, max_length=500, description="Item description to map")
    unit_price: Optional[float] = Field(None, ge=0, description="Unit price for context")
    quantity: Optional[float] = Field(1.0, ge=0, description="Quantity for context")
    use_ai: bool = Field(True, description="Whether to use AI-powered mapping")


class DescriptionMappingResponse(BaseModel):
    """Schema for description mapping response"""
    account_code: str
    account_name: str
    confidence_score: float
    mapping_source: str
    category: str
    subcategory: Optional[str]
    suggested_alternatives: List[str] = Field(default_factory=list)


class TVAAccountsResponse(BaseModel):
    """Schema for TVA accounts response"""
    deductible_accounts: Dict[str, str]
    collectee_accounts: Dict[str, str]
    rate_mapping: Dict[float, Dict[str, str]]


# ==========================================
# ACCOUNT MANAGEMENT ENDPOINTS
# ==========================================

@router.get("/accounts", response_model=List[PCGAccountResponse])
async def list_pcg_accounts(
    category: Optional[str] = Query(None, description="Filter by account category"),
    search: Optional[str] = Query(None, description="Search in account name, code, or keywords"),
    active_only: bool = Query(True, description="Return only active accounts"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    List and search PCG accounts
    
    Provides comprehensive listing with filtering and search capabilities
    for expert-comptables to find appropriate account codes.
    """
    try:
        crud = get_pcg_crud(db)
        
        if search:
            # Search functionality
            accounts = crud.search_accounts(search, category, limit)
        elif category:
            # Filter by category
            accounts = crud.get_accounts_by_category(category, active_only=active_only)
            accounts = accounts[offset:offset + limit]
        else:
            # Get all accounts with pagination
            query = db.query(PlanComptableGeneral)
            if active_only:
                query = query.filter(PlanComptableGeneral.is_active == True)
            
            accounts = query.order_by(PlanComptableGeneral.account_code).offset(offset).limit(limit).all()
        
        logger.info(f"Retrieved {len(accounts)} PCG accounts (category: {category}, search: {search})")
        return accounts
        
    except Exception as e:
        logger.error(f"Failed to list PCG accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve PCG accounts: {str(e)}"
        )


@router.get("/accounts/{account_code}", response_model=PCGAccountResponse)
async def get_pcg_account(
    account_code: str,
    db: Session = Depends(get_db)
):
    """
    Get specific PCG account details by account code
    
    Returns complete account information including software mappings
    and keywords for expert-comptable reference.
    """
    try:
        crud = get_pcg_crud(db)
        account = crud.get_account_by_code(account_code)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PCG account {account_code} not found"
            )
        
        logger.info(f"Retrieved PCG account: {account_code}")
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PCG account {account_code}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve PCG account: {str(e)}"
        )


@router.post("/accounts", response_model=PCGAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_pcg_account(
    account_data: PCGAccountCreate,
    db: Session = Depends(get_db)
    # TODO: Add admin authentication dependency
):
    """
    Create a new PCG account (admin only)
    
    Allows expert-comptables to create custom account codes
    for specialized business needs.
    """
    try:
        crud = get_pcg_crud(db)
        
        account = crud.create_account(
            account_code=account_data.account_code,
            account_name=account_data.account_name,
            account_category=account_data.account_category,
            account_subcategory=account_data.account_subcategory,
            vat_applicable=account_data.vat_applicable,
            default_vat_rate=account_data.default_vat_rate,
            keywords=account_data.keywords,
            sage_mapping=account_data.sage_mapping,
            ebp_mapping=account_data.ebp_mapping,
            ciel_mapping=account_data.ciel_mapping
        )
        
        logger.info(f"Created PCG account: {account.account_code} - {account.account_name}")
        return account
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create PCG account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create PCG account: {str(e)}"
        )


@router.put("/accounts/{account_id}", response_model=PCGAccountResponse)
async def update_pcg_account(
    account_id: UUID,
    account_updates: PCGAccountUpdate,
    db: Session = Depends(get_db)
    # TODO: Add admin authentication dependency
):
    """
    Update PCG account (admin only)
    
    Allows modifications to account names, categories, keywords,
    and software mappings for ongoing maintenance.
    """
    try:
        crud = get_pcg_crud(db)
        
        # Convert Pydantic model to dict, excluding None values
        updates = account_updates.dict(exclude_unset=True)
        
        account = crud.update_account(account_id, updates)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PCG account {account_id} not found"
            )
        
        logger.info(f"Updated PCG account: {account.account_code}")
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update PCG account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update PCG account: {str(e)}"
        )


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pcg_account(
    account_id: UUID,
    hard_delete: bool = Query(False, description="Whether to permanently delete (default: soft delete)"),
    db: Session = Depends(get_db)
    # TODO: Add admin authentication dependency
):
    """
    Delete PCG account (admin only)
    
    Soft delete by default (sets is_active=False) to preserve
    historical accounting data integrity.
    """
    try:
        crud = get_pcg_crud(db)
        
        success = crud.delete_account(account_id, soft_delete=not hard_delete)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PCG account {account_id} not found"
            )
        
        delete_type = "hard" if hard_delete else "soft"
        logger.info(f"Performed {delete_type} delete of PCG account: {account_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete PCG account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete PCG account: {str(e)}"
        )


# ==========================================
# INTELLIGENT MAPPING ENDPOINTS
# ==========================================

@router.post("/map-description", response_model=DescriptionMappingResponse)
async def map_description_to_account(
    mapping_request: DescriptionMappingRequest,
    db: Session = Depends(get_db)
):
    """
    Map invoice description to appropriate PCG account code
    
    Uses AI-powered intelligent mapping to suggest the most appropriate
    French accounting code based on item description and context.
    """
    try:
        pcg_service = get_pcg_service(db)
        
        # Create line item for mapping
        line_item = LineItem(
            description=mapping_request.description,
            unit_price=mapping_request.unit_price or 0.0,
            quantity=mapping_request.quantity or 1.0,
            total=(mapping_request.unit_price or 0.0) * (mapping_request.quantity or 1.0)
        )
        
        # Perform intelligent mapping
        mapping_result = pcg_service.map_line_item_to_account(line_item, mapping_request.use_ai)
        
        logger.info(f"Mapped '{mapping_request.description[:30]}' to {mapping_result.account_code} "
                   f"(confidence: {mapping_result.confidence_score:.2f})")
        
        return DescriptionMappingResponse(
            account_code=mapping_result.account_code,
            account_name=mapping_result.account_name,
            confidence_score=mapping_result.confidence_score,
            mapping_source=mapping_result.mapping_source,
            category=mapping_result.category,
            subcategory=mapping_result.subcategory,
            suggested_alternatives=mapping_result.suggested_alternatives or []
        )
        
    except Exception as e:
        logger.error(f"Failed to map description to account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to map description: {str(e)}"
        )


@router.get("/categories")
async def get_account_categories(db: Session = Depends(get_db)):
    """
    Get organized account categories for UI selection
    
    Returns account codes grouped by logical categories to help
    expert-comptables quickly find appropriate accounts.
    """
    try:
        # Get static category mapping
        static_categories = get_category_account_mapping()
        
        # Enhance with dynamic data from database
        crud = get_pcg_crud(db)
        
        enhanced_categories = {}
        for category_name, account_codes in static_categories.items():
            enhanced_categories[category_name] = []
            
            for code in account_codes:
                account = crud.get_account_by_code(code)
                if account:
                    enhanced_categories[category_name].append({
                        "code": account.account_code,
                        "name": account.account_name,
                        "vat_applicable": account.vat_applicable,
                        "default_vat_rate": account.default_vat_rate
                    })
        
        logger.info(f"Retrieved {len(enhanced_categories)} account categories")
        return {
            "categories": enhanced_categories,
            "total_categories": len(enhanced_categories)
        }
        
    except Exception as e:
        logger.error(f"Failed to get account categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve categories: {str(e)}"
        )


@router.get("/tva-accounts", response_model=TVAAccountsResponse)
async def get_tva_accounts(db: Session = Depends(get_db)):
    """
    Get TVA-specific account codes by rate and type
    
    Returns organized TVA accounts for deductible and collectée
    with rate-specific mappings for expert-comptable reference.
    """
    try:
        crud = get_pcg_crud(db)
        pcg_service = get_pcg_service(db)
        
        # Get TVA accounts from database
        deductible_accounts_db = crud.get_tva_accounts(deductible=True)
        collectee_accounts_db = crud.get_tva_accounts(deductible=False)
        
        # Format deductible accounts
        deductible_accounts = {}
        for account in deductible_accounts_db:
            deductible_accounts[account.account_code] = account.account_name
        
        # Format collectée accounts
        collectee_accounts = {}
        for account in collectee_accounts_db:
            collectee_accounts[account.account_code] = account.account_name
        
        # Get rate mapping
        rate_mapping = get_tva_mapping_by_rate()
        
        logger.info(f"Retrieved {len(deductible_accounts)} deductible and {len(collectee_accounts)} collectée TVA accounts")
        
        return TVAAccountsResponse(
            deductible_accounts=deductible_accounts,
            collectee_accounts=collectee_accounts,
            rate_mapping=rate_mapping
        )
        
    except Exception as e:
        logger.error(f"Failed to get TVA accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve TVA accounts: {str(e)}"
        )


# ==========================================
# STATISTICS AND MONITORING ENDPOINTS
# ==========================================

@router.get("/statistics")
async def get_pcg_statistics(db: Session = Depends(get_db)):
    """
    Get PCG usage and coverage statistics
    
    Provides insights into account usage, coverage, and system
    health for expert-comptable monitoring and optimization.
    """
    try:
        crud = get_pcg_crud(db)
        statistics = crud.get_account_statistics()
        
        # Add additional computed statistics
        if statistics:
            statistics["coverage_percentage"] = (
                (statistics.get("active_accounts", 0) / max(statistics.get("total_accounts", 1), 1)) * 100
            )
            
            statistics["tva_account_coverage"] = {
                "deductible": statistics.get("tva_deductible_accounts", 0),
                "collectee": statistics.get("tva_collectee_accounts", 0),
                "total": statistics.get("tva_deductible_accounts", 0) + statistics.get("tva_collectee_accounts", 0)
            }
        
        logger.info("Retrieved PCG statistics")
        return statistics
        
    except Exception as e:
        logger.error(f"Failed to get PCG statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


# ==========================================
# UTILITY ENDPOINTS
# ==========================================

@router.get("/software-mapping/{account_code}")
async def get_software_mapping(
    account_code: str,
    software: str = Query(..., description="Software name (sage, ebp, ciel)"),
    db: Session = Depends(get_db)
):
    """
    Get account code mapping for specific accounting software
    
    Returns software-specific account codes for seamless integration
    with existing expert-comptable workflows.
    """
    try:
        pcg_service = get_pcg_service(db)
        
        if software.lower() not in ['sage', 'ebp', 'ciel']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Software must be one of: sage, ebp, ciel"
            )
        
        mapping = pcg_service.get_software_mapping(account_code, software.lower())
        
        if mapping is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {software} mapping found for account {account_code}"
            )
        
        logger.info(f"Retrieved {software} mapping for {account_code}: {mapping}")
        return {
            "pcg_code": account_code,
            "software": software.lower(),
            "software_code": mapping
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get software mapping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve software mapping: {str(e)}"
        )