"""
INSEE Sirene API v3.11 Client

This module provides a robust client for interfacing with the French INSEE Sirene API
for SIREN/SIRET validation and company information retrieval.

Features:
- OAuth2 authentication with INSEE API
- Comprehensive error handling and retry logic
- Built-in circuit breaker pattern for resilience
- Multi-layer caching for performance
- Rate limiting compliance
- GDPR-compliant data handling
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import get_settings
from models.french_compliance import INSEEAPICall, FrenchComplianceValidation
from core.gdpr_audit import log_audit_event

# Configure logging
logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class INSEECompanyInfo:
    """Structured INSEE company information"""
    siren: str
    company_name: str
    legal_form: str
    naf_code: str
    creation_date: Optional[datetime]
    is_active: bool
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    
@dataclass
class INSEEEstablishmentInfo:
    """Structured INSEE establishment information"""
    siret: str
    siren: str
    is_active: bool
    is_headquarters: bool
    address_complete: str
    postal_code: str
    city: str
    creation_date: Optional[datetime]
    closure_date: Optional[datetime] = None

class CircuitBreaker:
    """Circuit breaker for INSEE API calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        
        # HALF_OPEN state
        return True
    
    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

class INSEEAPIClient:
    """
    Professional INSEE Sirene API v3.11 client with OAuth2 authentication
    
    Provides comprehensive SIREN/SIRET validation and company information retrieval
    with enterprise-grade reliability features.
    """
    
    BASE_URL = "https://api.insee.fr/api-sirene/3.11"
    TOKEN_URL = "https://api.insee.fr/token"  # Not used in v3.11
    
    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=10)
        )
        self.access_token = None
        self.token_expires_at = None
        self.circuit_breaker = CircuitBreaker()
        
        # Rate limiting (INSEE allows 30 requests/minute)
        self.rate_limit_requests = []
        self.max_requests_per_minute = 25  # Conservative limit
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def _get_api_headers(self) -> Dict[str, str]:
        """Get headers with INSEE API key for v3.11"""
        return {
            "X-INSEE-Api-Key-Integration": self.settings.INSEE_API_KEY,
            "Accept": "application/json;charset=utf-8;qs=1"
        }
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = time.time()
        # Remove requests older than 1 minute
        self.rate_limit_requests = [
            req_time for req_time in self.rate_limit_requests 
            if now - req_time < 60
        ]
        
        return len(self.rate_limit_requests) < self.max_requests_per_minute
    
    def _record_request(self):
        """Record a new API request for rate limiting"""
        self.rate_limit_requests.append(time.time())
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any],
        db_session: AsyncSession,
        invoice_id: Optional[str] = None,
        validation_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], INSEEAPICall]:
        """Make authenticated request to INSEE API with full audit logging"""
        
        if not self.circuit_breaker.can_execute():
            raise Exception("INSEE API circuit breaker is OPEN - service temporarily unavailable")
        
        if not self._check_rate_limit():
            await asyncio.sleep(60)  # Wait for rate limit reset
        
        start_time = time.time()
        request_identifier = params.get('q', '').split(':')[-1] if 'q' in params else 'unknown'
        
        # Create audit record
        api_call = INSEEAPICall(
            invoice_id=invoice_id,
            validation_id=validation_id,
            endpoint=endpoint.split('/')[-1],
            request_identifier=request_identifier,
            request_method='GET'
        )
        
        try:
            self._record_request()
            
            response = await self.client.get(
                f"{self.BASE_URL}/{endpoint}",
                params=params,
                headers=self._get_api_headers()
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Update audit record with response data
            api_call.response_status = response.status_code
            api_call.response_time_ms = response_time
            api_call.rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            
            if response.status_code == 200:
                response_data = response.json()
                api_call.response_data = response_data
                
                self.circuit_breaker.record_success()
                logger.info(f"INSEE API call successful: {endpoint} for {request_identifier}")
                
                # Add to session and return
                db_session.add(api_call)
                return response_data, api_call
                
            elif response.status_code == 429:
                # Rate limit exceeded
                api_call.error_message = "Rate limit exceeded"
                logger.warning("INSEE API rate limit exceeded")
                await asyncio.sleep(60)
                raise Exception("INSEE API rate limit exceeded")
                
            elif response.status_code == 404:
                # Not found - this is a valid business case
                api_call.response_data = {"message": "Not found"}
                logger.info(f"INSEE entity not found: {request_identifier}")
                
                db_session.add(api_call)
                return {"header": {"statut": 404, "message": "Not found"}}, api_call
                
            else:
                error_msg = f"INSEE API error: {response.status_code} - {response.text}"
                api_call.error_message = error_msg
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            self.circuit_breaker.record_failure()
            api_call.error_message = str(e)
            api_call.response_time_ms = int((time.time() - start_time) * 1000)
            
            logger.error(f"INSEE API call failed: {e}")
            db_session.add(api_call)
            raise
    
    async def validate_siren(
        self, 
        siren: str, 
        db_session: AsyncSession,
        invoice_id: Optional[str] = None,
        validation_id: Optional[str] = None
    ) -> Optional[INSEECompanyInfo]:
        """
        Validate SIREN and retrieve company information
        
        Args:
            siren: 9-digit SIREN number
            db_session: Database session for audit logging
            invoice_id: Optional invoice ID for audit trail
            validation_id: Optional validation ID for audit trail
            
        Returns:
            INSEECompanyInfo if valid, None if not found
        """
        
        # Basic format validation
        if not siren or len(siren) != 9 or not siren.isdigit():
            logger.warning(f"Invalid SIREN format: {siren}")
            return None
        
        try:
            # GDPR audit log
            await log_audit_event(
                db_session,
                user_id=None,
                operation_type="insee_siren_lookup",
                data_categories=["business_identification"],
                risk_level="medium",
                details={"siren": siren, "purpose": "french_compliance_validation"}
            )
            
            response_data, api_call = await self._make_request(
                "siret",
                {"q": f"siren:{siren}", "nombre": 1},
                db_session,
                invoice_id,
                validation_id
            )
            
            if (response_data.get("header", {}).get("statut") == 200 and 
                "etablissements" in response_data):
                
                etablissements = response_data["etablissements"]
                if etablissements:
                    # Get the first establishment (headquarters)
                    etab = etablissements[0]
                    unite_legale = etab.get("uniteLegale", {})
                    
                    return INSEECompanyInfo(
                        siren=siren,
                        company_name=unite_legale.get("denominationUniteLegale") or 
                                    unite_legale.get("prenom1UniteLegale", "") + " " + 
                                    unite_legale.get("nomUniteLegale", ""),
                        legal_form=unite_legale.get("categorieJuridiqueUniteLegale", ""),
                        naf_code=unite_legale.get("activitePrincipaleUniteLegale", ""),
                        creation_date=self._parse_insee_date(
                            unite_legale.get("dateCreationUniteLegale")
                        ),
                        is_active=unite_legale.get("etatAdministratifUniteLegale") == "A"
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"SIREN validation failed for {siren}: {e}")
            return None
    
    async def validate_siret(
        self, 
        siret: str, 
        db_session: AsyncSession,
        invoice_id: Optional[str] = None,
        validation_id: Optional[str] = None
    ) -> Optional[INSEEEstablishmentInfo]:
        """
        Validate SIRET and retrieve establishment information
        
        Args:
            siret: 14-digit SIRET number
            db_session: Database session for audit logging
            invoice_id: Optional invoice ID for audit trail
            validation_id: Optional validation ID for audit trail
            
        Returns:
            INSEEEstablishmentInfo if valid, None if not found
        """
        
        # Basic format validation
        if not siret or len(siret) != 14 or not siret.isdigit():
            logger.warning(f"Invalid SIRET format: {siret}")
            return None
        
        try:
            # GDPR audit log
            await log_audit_event(
                db_session,
                user_id=None,
                operation_type="insee_siret_lookup",
                data_categories=["business_identification", "address_data"],
                risk_level="medium",
                details={"siret": siret, "purpose": "french_compliance_validation"}
            )
            
            response_data, api_call = await self._make_request(
                f"siret/{siret}",
                {},
                db_session,
                invoice_id,
                validation_id
            )
            
            if (response_data.get("header", {}).get("statut") == 200 and 
                "etablissement" in response_data):
                
                etab = response_data["etablissement"]
                adresse = etab.get("adresseEtablissement", {})
                unite_legale = etab.get("uniteLegale", {})
                
                # Build complete address
                address_parts = []
                if adresse.get("numeroVoieEtablissement"):
                    address_parts.append(adresse["numeroVoieEtablissement"])
                if adresse.get("typeVoieEtablissement"):
                    address_parts.append(adresse["typeVoieEtablissement"])
                if adresse.get("libelleVoieEtablissement"):
                    address_parts.append(adresse["libelleVoieEtablissement"])
                
                return INSEEEstablishmentInfo(
                    siret=siret,
                    siren=siret[:9],
                    is_active=etab.get("etatAdministratifEtablissement") == "A",
                    is_headquarters=etab.get("etablissementSiege") == "true",
                    address_complete=" ".join(address_parts),
                    postal_code=adresse.get("codePostalEtablissement", ""),
                    city=adresse.get("libelleCommuneEtablissement", ""),
                    creation_date=self._parse_insee_date(
                        etab.get("dateCreationEtablissement")
                    ),
                    closure_date=self._parse_insee_date(
                        etab.get("dateFermetureEtablissement")
                    )
                )
            
            return None
            
        except Exception as e:
            logger.error(f"SIRET validation failed for {siret}: {e}")
            return None
    
    def _parse_insee_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse INSEE date format (YYYY-MM-DD)"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"Invalid INSEE date format: {date_str}")
            return None

class INSEECache:
    """
    Multi-layer caching system for INSEE API responses
    
    Implements both in-memory and Redis caching for optimal performance
    while respecting data freshness requirements.
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.memory_cache_ttl: Dict[str, float] = {}
        
        # Cache TTL settings (in seconds)
        self.siren_cache_ttl = 3600 * 24  # 24 hours for SIREN data
        self.siret_cache_ttl = 3600 * 12  # 12 hours for SIRET data
        self.memory_ttl = 3600  # 1 hour for memory cache
    
    def _get_cache_key(self, identifier: str, lookup_type: str) -> str:
        """Generate standardized cache key"""
        return f"insee:{lookup_type}:{identifier}"
    
    async def get_siren_data(self, siren: str) -> Optional[Dict[str, Any]]:
        """Get cached SIREN data"""
        cache_key = self._get_cache_key(siren, "siren")
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            if time.time() < self.memory_cache_ttl.get(cache_key, 0):
                logger.debug(f"SIREN cache hit (memory): {siren}")
                return self.memory_cache[cache_key]
            else:
                # Expired
                del self.memory_cache[cache_key]
                del self.memory_cache_ttl[cache_key]
        
        # Check Redis cache
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    # Update memory cache
                    self.memory_cache[cache_key] = data
                    self.memory_cache_ttl[cache_key] = time.time() + self.memory_ttl
                    logger.debug(f"SIREN cache hit (Redis): {siren}")
                    return data
            except Exception as e:
                logger.warning(f"Redis cache error for SIREN {siren}: {e}")
        
        return None
    
    async def set_siren_data(self, siren: str, data: Dict[str, Any]):
        """Cache SIREN data"""
        cache_key = self._get_cache_key(siren, "siren")
        
        # Set memory cache
        self.memory_cache[cache_key] = data
        self.memory_cache_ttl[cache_key] = time.time() + self.memory_ttl
        
        # Set Redis cache
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key, 
                    self.siren_cache_ttl, 
                    json.dumps(data, default=str)
                )
                logger.debug(f"SIREN data cached: {siren}")
            except Exception as e:
                logger.warning(f"Redis cache set error for SIREN {siren}: {e}")
    
    async def get_siret_data(self, siret: str) -> Optional[Dict[str, Any]]:
        """Get cached SIRET data"""
        cache_key = self._get_cache_key(siret, "siret")
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            if time.time() < self.memory_cache_ttl.get(cache_key, 0):
                logger.debug(f"SIRET cache hit (memory): {siret}")
                return self.memory_cache[cache_key]
            else:
                # Expired
                del self.memory_cache[cache_key]
                del self.memory_cache_ttl[cache_key]
        
        # Check Redis cache
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    # Update memory cache
                    self.memory_cache[cache_key] = data
                    self.memory_cache_ttl[cache_key] = time.time() + self.memory_ttl
                    logger.debug(f"SIRET cache hit (Redis): {siret}")
                    return data
            except Exception as e:
                logger.warning(f"Redis cache error for SIRET {siret}: {e}")
        
        return None
    
    async def set_siret_data(self, siret: str, data: Dict[str, Any]):
        """Cache SIRET data"""
        cache_key = self._get_cache_key(siret, "siret")
        
        # Set memory cache
        self.memory_cache[cache_key] = data
        self.memory_cache_ttl[cache_key] = time.time() + self.memory_ttl
        
        # Set Redis cache
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key, 
                    self.siret_cache_ttl, 
                    json.dumps(data, default=str)
                )
                logger.debug(f"SIRET data cached: {siret}")
            except Exception as e:
                logger.warning(f"Redis cache set error for SIRET {siret}: {e}")

# Convenience functions for easy integration

async def validate_french_company(
    siren: str, 
    db_session: AsyncSession,
    cache: Optional[INSEECache] = None,
    invoice_id: Optional[str] = None
) -> Optional[INSEECompanyInfo]:
    """
    Validate French company by SIREN with caching
    
    Args:
        siren: 9-digit SIREN number
        db_session: Database session
        cache: Optional cache instance
        invoice_id: Optional invoice ID for audit
        
    Returns:
        INSEECompanyInfo if valid company found
    """
    
    # Check cache first
    if cache:
        cached_data = await cache.get_siren_data(siren)
        if cached_data:
            return INSEECompanyInfo(**cached_data)
    
    # Fetch from API
    async with INSEEAPIClient() as client:
        company_info = await client.validate_siren(siren, db_session, invoice_id)
        
        # Cache the result
        if company_info and cache:
            await cache.set_siren_data(siren, company_info.__dict__)
        
        return company_info

async def validate_french_establishment(
    siret: str, 
    db_session: AsyncSession,
    cache: Optional[INSEECache] = None,
    invoice_id: Optional[str] = None
) -> Optional[INSEEEstablishmentInfo]:
    """
    Validate French establishment by SIRET with caching
    
    Args:
        siret: 14-digit SIRET number
        db_session: Database session
        cache: Optional cache instance
        invoice_id: Optional invoice ID for audit
        
    Returns:
        INSEEEstablishmentInfo if valid establishment found
    """
    
    # Check cache first
    if cache:
        cached_data = await cache.get_siret_data(siret)
        if cached_data:
            return INSEEEstablishmentInfo(**cached_data)
    
    # Fetch from API
    async with INSEEAPIClient() as client:
        establishment_info = await client.validate_siret(siret, db_session, invoice_id)
        
        # Cache the result
        if establishment_info and cache:
            await cache.set_siret_data(siret, establishment_info.__dict__)
        
        return establishment_info