"""
PCG Initialization Utility

Provides functions to initialize the Plan Comptable Général database
with standard French accounting codes for MVP functionality.

Usage:
    python -m core.pcg.init_pcg --init-essential
    python -m core.pcg.init_pcg --init-full
    python -m core.pcg.init_pcg --check-status
"""

import logging
import asyncio
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

from core.config import settings
from core.database import get_db
from crud.pcg import PCGAccountCRUD
from core.pcg.standard_accounts import get_standard_pcg_accounts, get_essential_pcg_accounts

logger = logging.getLogger(__name__)


class PCGInitializer:
    """Initialize Plan Comptable Général accounts in database"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.crud = PCGAccountCRUD(db_session)
    
    def check_initialization_status(self) -> Dict[str, Any]:
        """
        Check PCG initialization status
        
        Returns:
            Dictionary with initialization information
        """
        try:
            # Count existing accounts
            total_accounts = self.db.query(
                text("SELECT COUNT(*) FROM plan_comptable_general")
            ).scalar() or 0
            
            active_accounts = self.db.query(
                text("SELECT COUNT(*) FROM plan_comptable_general WHERE is_active = true")
            ).scalar() or 0
            
            # Check for essential accounts
            essential_codes = ["401000", "445662", "611000", "624100", "626000", "607000"]
            essential_present = 0
            
            for code in essential_codes:
                result = self.db.query(
                    text("SELECT COUNT(*) FROM plan_comptable_general WHERE account_code = :code")
                ).params(code=code).scalar()
                if result and result > 0:
                    essential_present += 1
            
            # Check categories
            categories_query = """
                SELECT account_category, COUNT(*) 
                FROM plan_comptable_general 
                WHERE is_active = true 
                GROUP BY account_category
            """
            categories = dict(self.db.execute(text(categories_query)).fetchall() or [])
            
            status = {
                "total_accounts": total_accounts,
                "active_accounts": active_accounts,
                "essential_accounts_present": essential_present,
                "essential_accounts_total": len(essential_codes),
                "essential_complete": essential_present == len(essential_codes),
                "categories": categories,
                "is_initialized": total_accounts > 0,
                "initialization_level": self._determine_initialization_level(
                    total_accounts, essential_present, len(essential_codes)
                )
            }
            
            logger.info(f"PCG Status: {status['initialization_level']} "
                       f"({status['active_accounts']} active accounts)")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to check PCG initialization status: {e}")
            return {
                "error": str(e),
                "is_initialized": False,
                "initialization_level": "error"
            }
    
    def initialize_essential_accounts(self) -> Dict[str, Any]:
        """
        Initialize essential PCG accounts for basic MVP functionality
        
        Returns:
            Dictionary with initialization results
        """
        try:
            logger.info("Initializing essential PCG accounts...")
            
            essential_accounts = get_essential_pcg_accounts()
            return self._bulk_insert_accounts(essential_accounts, "essential")
            
        except Exception as e:
            logger.error(f"Failed to initialize essential PCG accounts: {e}")
            return {
                "success": False,
                "error": str(e),
                "inserted": 0,
                "skipped": 0
            }
    
    def initialize_full_accounts(self) -> Dict[str, Any]:
        """
        Initialize full set of standard PCG accounts
        
        Returns:
            Dictionary with initialization results
        """
        try:
            logger.info("Initializing full set of PCG accounts...")
            
            standard_accounts = get_standard_pcg_accounts()
            return self._bulk_insert_accounts(standard_accounts, "full")
            
        except Exception as e:
            logger.error(f"Failed to initialize full PCG accounts: {e}")
            return {
                "success": False,
                "error": str(e),
                "inserted": 0,
                "skipped": 0
            }
    
    def validate_accounts(self) -> Dict[str, Any]:
        """
        Validate PCG accounts for consistency and compliance
        
        Returns:
            Dictionary with validation results
        """
        try:
            validation_results = {
                "valid_accounts": 0,
                "invalid_accounts": 0,
                "warnings": [],
                "errors": [],
                "duplicates": [],
                "missing_mappings": []
            }
            
            # Get all active accounts
            accounts = self.crud.get_accounts_by_category("charges", active_only=True)
            accounts.extend(self.crud.get_accounts_by_category("produits", active_only=True))
            accounts.extend(self.crud.get_accounts_by_category("tiers", active_only=True))
            
            for account in accounts:
                # Validate account code format
                if not self._validate_account_code_format(account.account_code):
                    validation_results["errors"].append(
                        f"Invalid code format: {account.account_code}"
                    )
                    validation_results["invalid_accounts"] += 1
                    continue
                
                # Check for software mappings
                if not any([account.sage_mapping, account.ebp_mapping, account.ciel_mapping]):
                    validation_results["missing_mappings"].append(account.account_code)
                    validation_results["warnings"].append(
                        f"No software mappings: {account.account_code}"
                    )
                
                # Check for keywords
                if not account.keywords or len(account.keywords) == 0:
                    validation_results["warnings"].append(
                        f"No keywords for mapping: {account.account_code}"
                    )
                
                validation_results["valid_accounts"] += 1
            
            # Check for duplicates
            duplicates_query = """
                SELECT account_code, COUNT(*) as count 
                FROM plan_comptable_general 
                GROUP BY account_code 
                HAVING COUNT(*) > 1
            """
            duplicates = self.db.execute(text(duplicates_query)).fetchall()
            validation_results["duplicates"] = [row[0] for row in duplicates]
            
            validation_results["is_valid"] = (
                len(validation_results["errors"]) == 0 and
                len(validation_results["duplicates"]) == 0
            )
            
            logger.info(f"PCG validation completed: {validation_results['valid_accounts']} valid, "
                       f"{validation_results['invalid_accounts']} invalid, "
                       f"{len(validation_results['warnings'])} warnings")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Failed to validate PCG accounts: {e}")
            return {
                "error": str(e),
                "is_valid": False
            }
    
    def _bulk_insert_accounts(self, accounts_data: List[Dict[str, Any]], level: str) -> Dict[str, Any]:
        """Bulk insert accounts with error handling"""
        
        results = {
            "success": False,
            "level": level,
            "total": len(accounts_data),
            "inserted": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            for account_data in accounts_data:
                try:
                    # Check if account exists
                    existing = self.crud.get_account_by_code(account_data["account_code"])
                    if existing:
                        logger.debug(f"Skipping existing account: {account_data['account_code']}")
                        results["skipped"] += 1
                        continue
                    
                    # Create account
                    account = self.crud.create_account(
                        account_code=account_data["account_code"],
                        account_name=account_data["account_name"],
                        account_category=account_data["account_category"],
                        account_subcategory=account_data.get("account_subcategory"),
                        vat_applicable=account_data.get("vat_applicable", True),
                        default_vat_rate=account_data.get("default_vat_rate"),
                        keywords=account_data.get("keywords", []),
                        sage_mapping=account_data.get("sage_mapping"),
                        ebp_mapping=account_data.get("ebp_mapping"),
                        ciel_mapping=account_data.get("ciel_mapping")
                    )
                    
                    logger.info(f"Created account: {account.account_code} - {account.account_name}")
                    results["inserted"] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to create account {account_data.get('account_code', 'unknown')}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["success"] = results["inserted"] > 0 or results["skipped"] > 0
            
            logger.info(f"PCG {level} initialization completed: "
                       f"{results['inserted']} inserted, {results['skipped']} skipped, "
                       f"{len(results['errors'])} errors")
            
            return results
            
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            results["errors"].append(str(e))
            return results
    
    def _determine_initialization_level(self, total: int, essential: int, essential_total: int) -> str:
        """Determine initialization level based on account counts"""
        
        if total == 0:
            return "none"
        elif essential == essential_total and total >= 20:
            return "full"
        elif essential >= essential_total - 1:  # Allow 1 missing essential
            return "essential"
        elif total > 0:
            return "partial"
        else:
            return "incomplete"
    
    def _validate_account_code_format(self, code: str) -> bool:
        """Validate French account code format"""
        
        if not code or len(code) < 3:
            return False
        
        # Must start with digit 1-7 (French accounting classes)
        if not code[0].isdigit() or code[0] not in '1234567':
            return False
        
        # Must be all digits
        if not code.isdigit():
            return False
        
        # Reasonable length
        if len(code) > 10:
            return False
        
        return True


# ==========================================
# ASYNC CONVENIENCE FUNCTIONS
# ==========================================

async def initialize_pcg_essential():
    """Async wrapper for essential PCG initialization"""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    db = Session(engine)
    
    try:
        initializer = PCGInitializer(db)
        result = initializer.initialize_essential_accounts()
        return result
    finally:
        db.close()


async def initialize_pcg_full():
    """Async wrapper for full PCG initialization"""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    db = Session(engine)
    
    try:
        initializer = PCGInitializer(db)
        result = initializer.initialize_full_accounts()
        return result
    finally:
        db.close()


async def check_pcg_status():
    """Async wrapper for PCG status check"""
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    db = Session(engine)
    
    try:
        initializer = PCGInitializer(db)
        result = initializer.check_initialization_status()
        return result
    finally:
        db.close()


# ==========================================
# CLI INTERFACE
# ==========================================

def main():
    """Main CLI interface for PCG initialization"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize Plan Comptable Général accounts")
    parser.add_argument("--init-essential", action="store_true", 
                       help="Initialize essential PCG accounts")
    parser.add_argument("--init-full", action="store_true", 
                       help="Initialize full set of PCG accounts")
    parser.add_argument("--check-status", action="store_true", 
                       help="Check PCG initialization status")
    parser.add_argument("--validate", action="store_true", 
                       help="Validate existing PCG accounts")
    
    args = parser.parse_args()
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    db = Session(engine)
    
    try:
        initializer = PCGInitializer(db)
        
        if args.check_status:
            print("Checking PCG initialization status...")
            status = initializer.check_initialization_status()
            print(f"Status: {status}")
            
        elif args.init_essential:
            print("Initializing essential PCG accounts...")
            result = initializer.initialize_essential_accounts()
            print(f"Result: {result}")
            
        elif args.init_full:
            print("Initializing full PCG accounts...")
            result = initializer.initialize_full_accounts()
            print(f"Result: {result}")
            
        elif args.validate:
            print("Validating PCG accounts...")
            validation = initializer.validate_accounts()
            print(f"Validation: {validation}")
            
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"PCG initialization failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()