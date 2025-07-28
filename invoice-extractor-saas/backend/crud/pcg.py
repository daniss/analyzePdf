"""
CRUD operations for Plan Comptable Général (French Chart of Accounts)

Provides database operations for managing French accounting codes with
expert-comptable requirements and compliance features.
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from uuid import UUID

from models.french_compliance import PlanComptableGeneral
from core.pcg.pcg_service import PCGAccountCategory

logger = logging.getLogger(__name__)


class PCGAccountCRUD:
    """CRUD operations for Plan Comptable Général accounts"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_account(
        self,
        account_code: str,
        account_name: str,
        account_category: str,
        account_subcategory: Optional[str] = None,
        vat_applicable: bool = True,
        default_vat_rate: Optional[float] = None,
        keywords: Optional[List[str]] = None,
        sage_mapping: Optional[str] = None,
        ebp_mapping: Optional[str] = None,
        ciel_mapping: Optional[str] = None
    ) -> PlanComptableGeneral:
        """
        Create a new PCG account
        
        Args:
            account_code: French account code (6-digit)
            account_name: Account name in French
            account_category: Account category (charges, produits, etc.)
            account_subcategory: Optional subcategory
            vat_applicable: Whether VAT applies to this account
            default_vat_rate: Default VAT rate for this account
            keywords: List of keywords for automatic mapping
            sage_mapping: Sage software account mapping
            ebp_mapping: EBP software account mapping
            ciel_mapping: Ciel software account mapping
            
        Returns:
            Created PCG account
        """
        try:
            # Validate account code format
            if not self._validate_account_code(account_code):
                raise ValueError(f"Invalid French account code format: {account_code}")
            
            # Check if account already exists
            existing = self.get_account_by_code(account_code)
            if existing:
                raise ValueError(f"Account code {account_code} already exists")
            
            # Create new account
            pcg_account = PlanComptableGeneral(
                account_code=account_code,
                account_name=account_name,
                account_category=account_category,
                account_subcategory=account_subcategory,
                vat_applicable=vat_applicable,
                default_vat_rate=default_vat_rate,
                keywords=keywords or [],
                sage_mapping=sage_mapping,
                ebp_mapping=ebp_mapping,
                ciel_mapping=ciel_mapping,
                is_active=True
            )
            
            self.db.add(pcg_account)
            self.db.commit()
            self.db.refresh(pcg_account)
            
            logger.info(f"Created PCG account: {account_code} - {account_name}")
            return pcg_account
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create PCG account {account_code}: {e}")
            raise
    
    def get_account_by_code(self, account_code: str) -> Optional[PlanComptableGeneral]:
        """Get PCG account by code"""
        return self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.account_code == account_code
        ).first()
    
    def get_account_by_id(self, account_id: UUID) -> Optional[PlanComptableGeneral]:
        """Get PCG account by ID"""
        return self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.id == account_id
        ).first()
    
    def get_accounts_by_category(
        self, 
        category: str, 
        subcategory: Optional[str] = None,
        active_only: bool = True
    ) -> List[PlanComptableGeneral]:
        """
        Get accounts by category and optional subcategory
        
        Args:
            category: Account category
            subcategory: Optional subcategory filter
            active_only: Whether to return only active accounts
            
        Returns:
            List of matching accounts
        """
        query = self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.account_category == category
        )
        
        if subcategory:
            query = query.filter(PlanComptableGeneral.account_subcategory == subcategory)
        
        if active_only:
            query = query.filter(PlanComptableGeneral.is_active == True)
        
        return query.order_by(PlanComptableGeneral.account_code).all()
    
    def search_accounts(
        self,
        search_term: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[PlanComptableGeneral]:
        """
        Search accounts by name, code, or keywords
        
        Args:
            search_term: Search term
            category: Optional category filter
            limit: Maximum results to return
            
        Returns:
            List of matching accounts
        """
        query = self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.is_active == True
        )
        
        # Add category filter if specified
        if category:
            query = query.filter(PlanComptableGeneral.account_category == category)
        
        # Create search filters
        search_filters = [
            PlanComptableGeneral.account_code.ilike(f'%{search_term}%'),
            PlanComptableGeneral.account_name.ilike(f'%{search_term}%'),
            PlanComptableGeneral.account_subcategory.ilike(f'%{search_term}%')
        ]
        
        # Add keyword search (JSON array contains)
        # Note: This is PostgreSQL-specific syntax
        search_filters.append(
            func.json_array_length(
                func.json_extract(PlanComptableGeneral.keywords, f'$[*]')
            ) > 0
        )
        
        query = query.filter(or_(*search_filters))
        
        return query.limit(limit).all()
    
    def get_accounts_by_class(self, account_class: int) -> List[PlanComptableGeneral]:
        """
        Get accounts by French accounting class (1-7)
        
        Args:
            account_class: French accounting class (1-7)
            
        Returns:
            List of accounts in the specified class
        """
        if account_class < 1 or account_class > 7:
            raise ValueError(f"Invalid French accounting class: {account_class}")
        
        # Account codes start with the class number
        class_prefix = str(account_class)
        
        return self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.account_code.like(f'{class_prefix}%'),
            PlanComptableGeneral.is_active == True
        ).order_by(PlanComptableGeneral.account_code).all()
    
    def update_account(
        self,
        account_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[PlanComptableGeneral]:
        """
        Update PCG account
        
        Args:
            account_id: Account ID to update
            updates: Dictionary of field updates
            
        Returns:
            Updated account or None if not found
        """
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                return None
            
            # Update allowed fields
            allowed_fields = {
                'account_name', 'account_category', 'account_subcategory',
                'vat_applicable', 'default_vat_rate', 'keywords',
                'sage_mapping', 'ebp_mapping', 'ciel_mapping', 'is_active'
            }
            
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(account, field, value)
            
            self.db.commit()
            self.db.refresh(account)
            
            logger.info(f"Updated PCG account: {account.account_code}")
            return account
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update PCG account {account_id}: {e}")
            raise
    
    def delete_account(self, account_id: UUID, soft_delete: bool = True) -> bool:
        """
        Delete PCG account (soft delete by default)
        
        Args:
            account_id: Account ID to delete
            soft_delete: Whether to soft delete (set is_active=False) or hard delete
            
        Returns:
            True if deleted successfully
        """
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                return False
            
            if soft_delete:
                account.is_active = False
                self.db.commit()
                logger.info(f"Soft deleted PCG account: {account.account_code}")
            else:
                self.db.delete(account)
                self.db.commit()
                logger.info(f"Hard deleted PCG account: {account.account_code}")
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete PCG account {account_id}: {e}")
            raise
    
    def get_tva_accounts(self, deductible: bool = True) -> List[PlanComptableGeneral]:
        """
        Get TVA-related accounts
        
        Args:
            deductible: True for TVA déductible, False for TVA collectée
            
        Returns:
            List of TVA accounts
        """
        if deductible:
            # TVA déductible accounts (4456xx)
            code_pattern = "4456%"
        else:
            # TVA collectée accounts (4457xx)
            code_pattern = "4457%"
        
        return self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.account_code.like(code_pattern),
            PlanComptableGeneral.is_active == True
        ).order_by(PlanComptableGeneral.account_code).all()
    
    def get_expense_accounts(self) -> List[PlanComptableGeneral]:
        """Get all expense accounts (Class 6)"""
        return self.get_accounts_by_class(6)
    
    def get_revenue_accounts(self) -> List[PlanComptableGeneral]:
        """Get all revenue accounts (Class 7)"""
        return self.get_accounts_by_class(7)
    
    def get_supplier_accounts(self) -> List[PlanComptableGeneral]:
        """Get supplier accounts (401xxx)"""
        return self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.account_code.like("401%"),
            PlanComptableGeneral.is_active == True
        ).order_by(PlanComptableGeneral.account_code).all()
    
    def get_customer_accounts(self) -> List[PlanComptableGeneral]:
        """Get customer accounts (411xxx)"""
        return self.db.query(PlanComptableGeneral).filter(
            PlanComptableGeneral.account_code.like("411%"),
            PlanComptableGeneral.is_active == True
        ).order_by(PlanComptableGeneral.account_code).all()
    
    def bulk_create_accounts(self, accounts_data: List[Dict[str, Any]]) -> List[PlanComptableGeneral]:
        """
        Bulk create multiple PCG accounts
        
        Args:
            accounts_data: List of account data dictionaries
            
        Returns:
            List of created accounts
        """
        try:
            created_accounts = []
            
            for account_data in accounts_data:
                # Skip if account already exists
                existing = self.get_account_by_code(account_data['account_code'])
                if existing:
                    logger.warning(f"Skipping existing account: {account_data['account_code']}")
                    continue
                
                account = PlanComptableGeneral(**account_data)
                self.db.add(account)
                created_accounts.append(account)
            
            self.db.commit()
            
            # Refresh all created accounts
            for account in created_accounts:
                self.db.refresh(account)
            
            logger.info(f"Bulk created {len(created_accounts)} PCG accounts")
            return created_accounts
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to bulk create PCG accounts: {e}")
            raise
    
    def get_account_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about PCG accounts
        
        Returns:
            Dictionary with account statistics
        """
        try:
            # Total accounts
            total_accounts = self.db.query(PlanComptableGeneral).count()
            active_accounts = self.db.query(PlanComptableGeneral).filter(
                PlanComptableGeneral.is_active == True
            ).count()
            
            # Accounts by category
            category_counts = {}
            for category in PCGAccountCategory:
                count = self.db.query(PlanComptableGeneral).filter(
                    PlanComptableGeneral.account_category == category.value,
                    PlanComptableGeneral.is_active == True
                ).count()
                category_counts[category.value] = count
            
            # Accounts by class
            class_counts = {}
            for class_num in range(1, 8):
                count = len(self.get_accounts_by_class(class_num))
                class_counts[f"Classe {class_num}"] = count
            
            return {
                "total_accounts": total_accounts,
                "active_accounts": active_accounts,
                "inactive_accounts": total_accounts - active_accounts,
                "accounts_by_category": category_counts,
                "accounts_by_class": class_counts,
                "tva_deductible_accounts": len(self.get_tva_accounts(deductible=True)),
                "tva_collectee_accounts": len(self.get_tva_accounts(deductible=False))
            }
            
        except Exception as e:
            logger.error(f"Failed to get account statistics: {e}")
            return {}
    
    def _validate_account_code(self, account_code: str) -> bool:
        """
        Validate French account code format
        
        Args:
            account_code: Account code to validate
            
        Returns:
            True if valid French account code format
        """
        if not account_code or len(account_code) < 3:
            return False
        
        # Must start with digit 1-7 (French accounting classes)
        if not account_code[0].isdigit() or account_code[0] not in '1234567':
            return False
        
        # Must be all digits
        if not account_code.isdigit():
            return False
        
        # Typical length is 6 digits, but can be longer for sub-accounts
        if len(account_code) > 10:
            return False
        
        return True


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def get_pcg_crud(db: Session) -> PCGAccountCRUD:
    """Factory function to get PCG CRUD instance"""
    return PCGAccountCRUD(db)


def create_standard_pcg_account(
    db: Session,
    code: str,
    name: str,
    category: str,
    keywords: List[str] = None
) -> PlanComptableGeneral:
    """
    Convenience function to create a standard PCG account
    
    Args:
        db: Database session
        code: Account code
        name: Account name
        category: Account category
        keywords: Keywords for mapping
        
    Returns:
        Created PCG account
    """
    crud = get_pcg_crud(db)
    return crud.create_account(
        account_code=code,
        account_name=name,
        account_category=category,
        keywords=keywords or []
    )