"""
Circuit Breaker Pattern Implementation

This module provides a robust circuit breaker implementation for external API calls,
specifically designed for the INSEE API and other French compliance services.

Features:
- Multiple circuit breaker states (CLOSED, OPEN, HALF_OPEN)
- Configurable failure thresholds and timeouts
- Automatic recovery mechanisms
- Health check integration
- Metrics and monitoring
- Thread-safe operations
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Calls blocked due to failures
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitMetrics:
    """Circuit breaker metrics and statistics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    total_response_time: float = 0.0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        if self.total_calls == 0:
            return 0.0
        return (self.failed_calls / self.total_calls) * 100
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time"""
        if self.successful_calls == 0:
            return 0.0
        return self.total_response_time / self.successful_calls

@dataclass
class CircuitConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5              # Number of failures before opening
    failure_rate_threshold: float = 50.0    # Failure rate percentage threshold
    recovery_timeout: int = 60              # Seconds before attempting recovery
    half_open_max_calls: int = 3            # Max calls in half-open state
    timeout: int = 30                       # Request timeout in seconds
    reset_timeout: int = 300                # Seconds before resetting metrics
    minimum_throughput: int = 10            # Minimum calls before rate calculation

class CircuitBreakerError(Exception):
    """Circuit breaker specific exception"""
    pass

class CircuitOpenError(CircuitBreakerError):
    """Exception raised when circuit is open"""
    pass

class CircuitBreaker:
    """
    Professional circuit breaker implementation for external API resilience
    
    Provides fault tolerance, automatic recovery, and detailed monitoring
    for external service dependencies.
    """
    
    def __init__(self, name: str, config: Optional[CircuitConfig] = None):
        self.name = name
        self.config = config or CircuitConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self.half_open_calls = 0
        self._lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenError: When circuit is open
            Exception: Original function exceptions when circuit allows
        """
        async with self._lock:
            # Check if call should be allowed
            if not await self._should_allow_call():
                self.metrics.rejected_calls += 1
                raise CircuitOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {self.metrics.last_failure_time}"
                )
            
            # Track call start
            self.metrics.total_calls += 1
            start_time = time.time()
            
            # In half-open state, limit concurrent calls
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
        
        try:
            # Execute function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            # Record success
            await self._record_success(time.time() - start_time)
            return result
            
        except Exception as e:
            # Record failure
            await self._record_failure(e)
            raise
        finally:
            # Reset half-open call counter
            if self.state == CircuitState.HALF_OPEN:
                async with self._lock:
                    self.half_open_calls = max(0, self.half_open_calls - 1)
    
    @asynccontextmanager
    async def protect(self):
        """
        Context manager for circuit breaker protection
        
        Usage:
            async with circuit_breaker.protect():
                result = await some_external_api_call()
        """
        if not await self._should_allow_call():
            raise CircuitOpenError(f"Circuit breaker '{self.name}' is OPEN")
        
        start_time = time.time()
        self.metrics.total_calls += 1
        
        try:
            yield
            await self._record_success(time.time() - start_time)
        except Exception as e:
            await self._record_failure(e)
            raise
    
    async def _should_allow_call(self) -> bool:
        """Determine if a call should be allowed based on current state"""
        current_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
        
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (self.metrics.last_failure_time and 
                current_time - self.metrics.last_failure_time > self.config.recovery_timeout):
                
                await self._transition_to_half_open()
                return True
            return False
        
        elif self.state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    async def _record_success(self, response_time: float):
        """Record successful call and update state if necessary"""
        async with self._lock:
            self.metrics.successful_calls += 1
            self.metrics.total_response_time += response_time
            self.metrics.last_success_time = time.time()
            
            # If in half-open state, transition to closed after success
            if self.state == CircuitState.HALF_OPEN:
                await self._transition_to_closed()
                logger.info(f"Circuit breaker '{self.name}' recovered - transitioning to CLOSED")
    
    async def _record_failure(self, error: Exception):
        """Record failed call and update state if necessary"""
        async with self._lock:
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = time.time()
            
            # Check if we should open the circuit
            if self._should_open_circuit():
                await self._transition_to_open()
                logger.warning(
                    f"Circuit breaker '{self.name}' opened due to failures. "
                    f"Failure rate: {self.metrics.failure_rate:.1f}%, "
                    f"Total failures: {self.metrics.failed_calls}"
                )
    
    def _should_open_circuit(self) -> bool:
        """Determine if circuit should be opened based on failure metrics"""
        # Must have minimum throughput before rate calculation
        if self.metrics.total_calls < self.config.minimum_throughput:
            return False
        
        # Check failure count threshold
        if self.metrics.failed_calls >= self.config.failure_threshold:
            return True
        
        # Check failure rate threshold
        if self.metrics.failure_rate >= self.config.failure_rate_threshold:
            return True
        
        return False
    
    async def _transition_to_open(self):
        """Transition circuit to OPEN state"""
        previous_state = self.state
        self.state = CircuitState.OPEN
        self.half_open_calls = 0
        self.metrics.state_changes += 1
        
        logger.warning(f"Circuit breaker '{self.name}': {previous_state.value} -> OPEN")
    
    async def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state"""
        previous_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.metrics.state_changes += 1
        
        logger.info(f"Circuit breaker '{self.name}': {previous_state.value} -> HALF_OPEN")
    
    async def _transition_to_closed(self):
        """Transition circuit to CLOSED state"""
        previous_state = self.state
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0
        self.metrics.state_changes += 1
        
        # Reset failure metrics on successful recovery
        self.metrics.failed_calls = 0
        self.metrics.last_failure_time = None
        
        logger.info(f"Circuit breaker '{self.name}': {previous_state.value} -> CLOSED")
    
    async def force_open(self):
        """Manually force circuit to OPEN state"""
        async with self._lock:
            await self._transition_to_open()
        logger.warning(f"Circuit breaker '{self.name}' manually forced OPEN")
    
    async def force_close(self):
        """Manually force circuit to CLOSED state"""
        async with self._lock:
            await self._transition_to_closed()
        logger.info(f"Circuit breaker '{self.name}' manually forced CLOSED")
    
    async def reset_metrics(self):
        """Reset all metrics and return to CLOSED state"""
        async with self._lock:
            self.metrics = CircuitMetrics()
            self.state = CircuitState.CLOSED
            self.half_open_calls = 0
        logger.info(f"Circuit breaker '{self.name}' metrics reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status and metrics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "failure_rate_threshold": self.config.failure_rate_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "timeout": self.config.timeout
            },
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "successful_calls": self.metrics.successful_calls,
                "failed_calls": self.metrics.failed_calls,
                "rejected_calls": self.metrics.rejected_calls,
                "failure_rate": round(self.metrics.failure_rate, 2),
                "average_response_time": round(self.metrics.average_response_time, 3),
                "state_changes": self.metrics.state_changes,
                "last_failure": (
                    datetime.fromtimestamp(self.metrics.last_failure_time).isoformat()
                    if self.metrics.last_failure_time else None
                ),
                "last_success": (
                    datetime.fromtimestamp(self.metrics.last_success_time).isoformat()
                    if self.metrics.last_success_time else None
                )
            },
            "half_open_calls": self.half_open_calls if self.state == CircuitState.HALF_OPEN else None
        }
    
    def is_healthy(self) -> bool:
        """Check if circuit breaker indicates healthy service"""
        return (
            self.state == CircuitState.CLOSED and 
            self.metrics.failure_rate < self.config.failure_rate_threshold
        )

class CircuitBreakerManager:
    """
    Centralized management of multiple circuit breakers
    
    Provides a registry for managing circuit breakers for different services
    with health monitoring and bulk operations.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(
        self, 
        name: str, 
        config: Optional[CircuitConfig] = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a service
        
        Args:
            name: Unique service name
            config: Optional configuration
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered circuit breakers"""
        return {
            name: breaker.get_status() 
            for name, breaker in self._breakers.items()
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary of all services"""
        if not self._breakers:
            return {"status": "no_breakers", "healthy_count": 0, "total_count": 0}
        
        healthy_count = sum(1 for breaker in self._breakers.values() if breaker.is_healthy())
        total_count = len(self._breakers)
        
        return {
            "status": "healthy" if healthy_count == total_count else "degraded",
            "healthy_count": healthy_count,
            "total_count": total_count,
            "health_percentage": round((healthy_count / total_count) * 100, 1),
            "degraded_services": [
                name for name, breaker in self._breakers.items() 
                if not breaker.is_healthy()
            ]
        }
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            await breaker.reset_metrics()
        logger.info(f"Reset {len(self._breakers)} circuit breakers")

# Global circuit breaker manager
_manager = CircuitBreakerManager()

def get_circuit_breaker(
    service_name: str, 
    config: Optional[CircuitConfig] = None
) -> CircuitBreaker:
    """
    Get circuit breaker for a service
    
    Args:
        service_name: Unique service identifier
        config: Optional circuit breaker configuration
        
    Returns:
        CircuitBreaker instance
    """
    return _manager.get_breaker(service_name, config)

def get_all_circuit_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all circuit breakers"""
    return _manager.get_all_status()

def get_circuit_health_summary() -> Dict[str, Any]:
    """Get health summary of all circuit breakers"""
    return _manager.get_health_summary()

# Pre-configured circuit breakers for French compliance services

def get_insee_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker configured for INSEE API"""
    config = CircuitConfig(
        failure_threshold=3,          # Open after 3 failures
        failure_rate_threshold=40.0,  # Open at 40% failure rate
        recovery_timeout=60,          # Try recovery after 1 minute
        half_open_max_calls=2,        # Limit half-open calls
        timeout=30,                   # 30 second timeout
        minimum_throughput=5          # Minimum calls for rate calculation
    )
    return get_circuit_breaker("insee_api", config)

def get_tva_validation_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker configured for TVA validation services"""
    config = CircuitConfig(
        failure_threshold=5,          # More tolerant for validation
        failure_rate_threshold=60.0,  # Higher threshold
        recovery_timeout=30,          # Faster recovery
        half_open_max_calls=3,
        timeout=15,                   # Shorter timeout
        minimum_throughput=10
    )
    return get_circuit_breaker("tva_validation", config)

async def reset_all_circuit_breakers():
    """Reset all circuit breakers - useful for testing and recovery"""
    await _manager.reset_all()