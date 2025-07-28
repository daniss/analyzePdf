"""
Multi-layer validation caching system

This module provides a comprehensive caching infrastructure for French compliance
validation data, implementing both in-memory and Redis caching strategies
with intelligent cache warming and TTL management.
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.config import get_settings
from models.french_compliance import (
    FrenchComplianceValidation, 
    ComplianceSettings,
    ValidationErrorPattern
)

logger = logging.getLogger(__name__)

class CacheLayer(Enum):
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"

@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

@dataclass
class CacheEntry:
    """Cached data entry with metadata"""
    data: Any
    timestamp: float
    ttl: int
    access_count: int = 0
    last_access: float = 0
    
    def is_expired(self) -> bool:
        return time.time() > (self.timestamp + self.ttl)
    
    def touch(self):
        self.access_count += 1
        self.last_access = time.time()

class ValidationCache:
    """
    High-performance multi-layer caching system for French compliance validation
    
    Features:
    - Memory cache with LRU eviction
    - Redis distributed cache
    - Intelligent cache warming
    - TTL-based expiration
    - Performance metrics
    - Cache coherence management
    """
    
    def __init__(self, redis_url: Optional[str] = None, max_memory_items: int = 1000):
        self.settings = get_settings()
        self.max_memory_items = max_memory_items
        
        # Memory cache (LRU)
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.memory_access_order: List[str] = []
        
        # Redis connection
        self.redis_client: Optional[redis.Redis] = None
        if redis_url or self.settings.REDIS_URL:
            try:
                self.redis_client = redis.from_url(
                    redis_url or self.settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None
        
        # Cache metrics
        self.metrics = {
            CacheLayer.MEMORY: CacheMetrics(),
            CacheLayer.REDIS: CacheMetrics(),
            CacheLayer.DATABASE: CacheMetrics()
        }
        
        # Cache key prefixes
        self.KEY_PREFIXES = {
            "siren": "fr_compliance:siren:",
            "siret": "fr_compliance:siret:",
            "tva": "fr_compliance:tva:",
            "validation": "fr_compliance:validation:",
            "settings": "fr_compliance:settings:",
            "error_pattern": "fr_compliance:error_pattern:"
        }
        
        # Default TTL values (seconds)
        self.DEFAULT_TTLS = {
            "siren": 86400,      # 24 hours
            "siret": 43200,      # 12 hours
            "tva": 3600,         # 1 hour
            "validation": 7200,  # 2 hours
            "settings": 1800,    # 30 minutes
            "error_pattern": 3600  # 1 hour
        }
    
    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """Generate standardized cache key"""
        return f"{self.KEY_PREFIXES[prefix]}{identifier}"
    
    def _evict_lru_memory(self):
        """Evict least recently used item from memory cache"""
        if not self.memory_access_order:
            return
        
        lru_key = self.memory_access_order.pop(0)
        if lru_key in self.memory_cache:
            del self.memory_cache[lru_key]
            self.metrics[CacheLayer.MEMORY].evictions += 1
    
    def _update_memory_access(self, key: str):
        """Update LRU access order for memory cache"""
        if key in self.memory_access_order:
            self.memory_access_order.remove(key)
        self.memory_access_order.append(key)
    
    async def get(
        self, 
        cache_type: str, 
        identifier: str, 
        db_session: Optional[AsyncSession] = None
    ) -> Optional[Any]:
        """
        Get cached data with multi-layer fallback
        
        Args:
            cache_type: Type of cached data (siren, siret, tva, etc.)
            identifier: Unique identifier for the data
            db_session: Optional database session for database fallback
            
        Returns:
            Cached data if found, None otherwise
        """
        cache_key = self._get_cache_key(cache_type, identifier)
        
        # Layer 1: Memory cache
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if not entry.is_expired():
                entry.touch()
                self._update_memory_access(cache_key)
                self.metrics[CacheLayer.MEMORY].hits += 1
                logger.debug(f"Memory cache hit: {cache_key}")
                return entry.data
            else:
                # Expired - remove from memory
                del self.memory_cache[cache_key]
                if cache_key in self.memory_access_order:
                    self.memory_access_order.remove(cache_key)
        
        self.metrics[CacheLayer.MEMORY].misses += 1
        
        # Layer 2: Redis cache
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    
                    # Populate memory cache
                    ttl = self.DEFAULT_TTLS.get(cache_type, 3600)
                    await self._set_memory_cache(cache_key, data, ttl)
                    
                    self.metrics[CacheLayer.REDIS].hits += 1
                    logger.debug(f"Redis cache hit: {cache_key}")
                    return data
            except Exception as e:
                logger.warning(f"Redis cache get error for {cache_key}: {e}")
                self.metrics[CacheLayer.REDIS].errors += 1
        
        self.metrics[CacheLayer.REDIS].misses += 1
        
        # Layer 3: Database fallback (for specific cache types)
        if db_session and cache_type in ["validation", "settings"]:
            try:
                data = await self._get_from_database(cache_type, identifier, db_session)
                if data:
                    # Cache the database result
                    await self.set(cache_type, identifier, data)
                    
                    self.metrics[CacheLayer.DATABASE].hits += 1
                    logger.debug(f"Database cache hit: {cache_key}")
                    return data
            except Exception as e:
                logger.warning(f"Database cache error for {cache_key}: {e}")
                self.metrics[CacheLayer.DATABASE].errors += 1
        
        self.metrics[CacheLayer.DATABASE].misses += 1
        return None
    
    async def set(
        self, 
        cache_type: str, 
        identifier: str, 
        data: Any, 
        ttl: Optional[int] = None
    ):
        """
        Set data in all available cache layers
        
        Args:
            cache_type: Type of cached data
            identifier: Unique identifier
            data: Data to cache
            ttl: Time to live in seconds (optional)
        """
        cache_key = self._get_cache_key(cache_type, identifier)
        ttl = ttl or self.DEFAULT_TTLS.get(cache_type, 3600)
        
        # Set in memory cache
        await self._set_memory_cache(cache_key, data, ttl)
        
        # Set in Redis cache
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(data, default=str)
                )
                self.metrics[CacheLayer.REDIS].sets += 1
                logger.debug(f"Redis cache set: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis cache set error for {cache_key}: {e}")
                self.metrics[CacheLayer.REDIS].errors += 1
    
    async def _set_memory_cache(self, key: str, data: Any, ttl: int):
        """Set data in memory cache with LRU eviction"""
        # Evict if necessary
        while len(self.memory_cache) >= self.max_memory_items:
            self._evict_lru_memory()
        
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl=ttl
        )
        entry.touch()
        
        self.memory_cache[key] = entry
        self._update_memory_access(key)
        self.metrics[CacheLayer.MEMORY].sets += 1
    
    async def _get_from_database(
        self, 
        cache_type: str, 
        identifier: str, 
        db_session: AsyncSession
    ) -> Optional[Any]:
        """Get data from database as cache fallback"""
        
        if cache_type == "validation":
            # Get latest validation result for invoice
            result = await db_session.execute(
                select(FrenchComplianceValidation)
                .where(FrenchComplianceValidation.invoice_id == identifier)
                .order_by(FrenchComplianceValidation.validation_timestamp.desc())
                .limit(1)
            )
            validation = result.scalar_one_or_none()
            return validation.to_dict() if validation else None
        
        elif cache_type == "settings":
            # Get compliance setting
            parts = identifier.split(":")
            if len(parts) == 2:
                category, name = parts
                setting = await ComplianceSettings.get_active_setting(
                    category, name, db_session
                )
                return setting.setting_value if setting else None
        
        return None
    
    async def invalidate(self, cache_type: str, identifier: str):
        """Invalidate cached data across all layers"""
        cache_key = self._get_cache_key(cache_type, identifier)
        
        # Remove from memory cache
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
            if cache_key in self.memory_access_order:
                self.memory_access_order.remove(cache_key)
        
        # Remove from Redis cache
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                logger.debug(f"Redis cache invalidated: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis cache invalidation error for {cache_key}: {e}")
    
    async def invalidate_pattern(self, cache_type: str, pattern: str = "*"):
        """Invalidate multiple cache entries by pattern"""
        prefix = self.KEY_PREFIXES[cache_type]
        full_pattern = f"{prefix}{pattern}"
        
        # Invalidate memory cache
        keys_to_remove = [
            key for key in self.memory_cache.keys() 
            if key.startswith(prefix)
        ]
        for key in keys_to_remove:
            del self.memory_cache[key]
            if key in self.memory_access_order:
                self.memory_access_order.remove(key)
        
        # Invalidate Redis cache
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(full_pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.debug(f"Redis pattern invalidated: {full_pattern} ({len(keys)} keys)")
            except Exception as e:
                logger.warning(f"Redis pattern invalidation error for {full_pattern}: {e}")
    
    async def warm_cache(self, db_session: AsyncSession):
        """
        Pre-populate cache with frequently accessed data
        
        This method loads commonly used validation settings and error patterns
        into the cache to improve initial response times.
        """
        logger.info("Starting cache warming process")
        
        try:
            # Warm compliance settings
            settings_result = await db_session.execute(
                select(ComplianceSettings).where(ComplianceSettings.is_active == True)
            )
            settings = settings_result.scalars().all()
            
            for setting in settings:
                cache_key = f"{setting.setting_category}:{setting.setting_name}"
                await self.set("settings", cache_key, setting.setting_value)
            
            logger.info(f"Warmed {len(settings)} compliance settings")
            
            # Warm frequently used error patterns
            patterns_result = await db_session.execute(
                select(ValidationErrorPattern)
                .order_by(ValidationErrorPattern.occurrence_count.desc())
                .limit(100)
            )
            patterns = patterns_result.scalars().all()
            
            for pattern in patterns:
                cache_key = f"{pattern.error_type}:{pattern.error_subtype or 'default'}"
                pattern_data = {
                    "pattern_data": pattern.pattern_data,
                    "suggested_fixes": pattern.suggested_fixes,
                    "success_rate": float(pattern.resolution_success_rate or 0)
                }
                await self.set("error_pattern", cache_key, pattern_data)
            
            logger.info(f"Warmed {len(patterns)} error patterns")
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache performance metrics"""
        return {
            "memory": {
                "hits": self.metrics[CacheLayer.MEMORY].hits,
                "misses": self.metrics[CacheLayer.MEMORY].misses,
                "hit_rate": self.metrics[CacheLayer.MEMORY].hit_rate,
                "sets": self.metrics[CacheLayer.MEMORY].sets,
                "evictions": self.metrics[CacheLayer.MEMORY].evictions,
                "current_size": len(self.memory_cache),
                "max_size": self.max_memory_items
            },
            "redis": {
                "hits": self.metrics[CacheLayer.REDIS].hits,
                "misses": self.metrics[CacheLayer.REDIS].misses,
                "hit_rate": self.metrics[CacheLayer.REDIS].hit_rate,
                "sets": self.metrics[CacheLayer.REDIS].sets,
                "errors": self.metrics[CacheLayer.REDIS].errors,
                "available": self.redis_client is not None
            },
            "database": {
                "hits": self.metrics[CacheLayer.DATABASE].hits,
                "misses": self.metrics[CacheLayer.DATABASE].misses,
                "hit_rate": self.metrics[CacheLayer.DATABASE].hit_rate,
                "errors": self.metrics[CacheLayer.DATABASE].errors
            }
        }
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all cache layers"""
        health = {
            "memory": True,  # Memory cache is always available
            "redis": False,
            "database": True  # Database health checked elsewhere
        }
        
        if self.redis_client:
            try:
                await self.redis_client.ping()
                health["redis"] = True
            except Exception:
                health["redis"] = False
        
        return health

# Singleton cache instance
_cache_instance: Optional[ValidationCache] = None

def get_validation_cache() -> ValidationCache:
    """Get singleton validation cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ValidationCache()
    return _cache_instance

async def initialize_cache(db_session: AsyncSession):
    """Initialize and warm the validation cache"""
    cache = get_validation_cache()
    await cache.warm_cache(db_session)
    logger.info("Validation cache initialized and warmed")

# Convenience functions for common cache operations

async def cache_siren_validation(
    siren: str, 
    validation_data: Dict[str, Any], 
    ttl: int = 86400
):
    """Cache SIREN validation result"""
    cache = get_validation_cache()
    await cache.set("siren", siren, validation_data, ttl)

async def get_cached_siren_validation(siren: str) -> Optional[Dict[str, Any]]:
    """Get cached SIREN validation result"""
    cache = get_validation_cache()
    return await cache.get("siren", siren)

async def cache_siret_validation(
    siret: str, 
    validation_data: Dict[str, Any], 
    ttl: int = 43200
):
    """Cache SIRET validation result"""
    cache = get_validation_cache()
    await cache.set("siret", siret, validation_data, ttl)

async def get_cached_siret_validation(siret: str) -> Optional[Dict[str, Any]]:
    """Get cached SIRET validation result"""
    cache = get_validation_cache()
    return await cache.get("siret", siret)

async def cache_tva_validation(
    tva_number: str, 
    validation_data: Dict[str, Any], 
    ttl: int = 3600
):
    """Cache TVA validation result"""
    cache = get_validation_cache()
    await cache.set("tva", tva_number, validation_data, ttl)

async def get_cached_tva_validation(tva_number: str) -> Optional[Dict[str, Any]]:
    """Get cached TVA validation result"""
    cache = get_validation_cache()
    return await cache.get("tva", tva_number)

async def invalidate_compliance_cache(identifier: str):
    """Invalidate all compliance-related cache entries for an identifier"""
    cache = get_validation_cache()
    
    # Try to invalidate as different types
    for cache_type in ["siren", "siret", "tva", "validation"]:
        await cache.invalidate(cache_type, identifier)