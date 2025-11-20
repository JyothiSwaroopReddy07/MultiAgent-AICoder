"""
Caching Utility for Performance Optimization
- In-memory LRU cache
- TTL (Time-To-Live) support
- Thread-safe operations
"""
import functools
import time
from typing import Any, Optional, Callable
from collections import OrderedDict
from threading import Lock
import structlog

from constants import CACHE_TTL, CACHE_MAX_SIZE

logger = structlog.get_logger()


class TTLCache:
    """
    Thread-safe LRU cache with TTL (Time-To-Live)
    
    Example:
        cache = TTLCache(max_size=100, ttl=3600)
        
        @cache.cached
        def expensive_operation(param):
            return result
    """
    
    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl: int = CACHE_TTL):
        """
        Args:
            max_size: Maximum number of items in cache
            ttl: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: dict = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            # Check if expired
            if time.time() - self._timestamps[key] > self.ttl:
                del self._cache[key]
                del self._timestamps[key]
                self._misses += 1
                logger.debug("cache_expired", key=key)
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug("cache_hit", key=key)
            return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    # Remove oldest item
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    del self._timestamps[oldest_key]
                    logger.debug("cache_evicted", key=oldest_key)
            
            self._cache[key] = value
            self._timestamps[key] = time.time()
            logger.debug("cache_set", key=key)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            logger.info("cache_cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "ttl": self.ttl
        }
    
    def cached(self, key_func: Optional[Callable] = None):
        """
        Decorator to cache function results
        
        Args:
            key_func: Optional function to generate cache key from args
            
        Example:
            @cache.cached(key_func=lambda x, y: f"{x}_{y}")
            def add(x, y):
                return x + y
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default: use function name and args
                    cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
                
                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result)
                
                return result
            
            return wrapper
        return decorator


# Global cache instance
_global_cache = TTLCache()


def cached(ttl: int = CACHE_TTL, key_func: Optional[Callable] = None):
    """
    Simple caching decorator using global cache
    
    Args:
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key
        
    Example:
        @cached(ttl=3600)
        def get_user(user_id):
            return fetch_user_from_db(user_id)
    """
    def decorator(func: Callable) -> Callable:
        cache = TTLCache(ttl=ttl)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            
            return result
        
        # Expose cache methods
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        wrapper.get_stats = cache.get_stats
        
        return wrapper
    
    return decorator


def memoize(func: Callable) -> Callable:
    """
    Simple memoization decorator (no TTL)
    
    Example:
        @memoize
        def fibonacci(n):
            if n < 2:
                return n
            return fibonacci(n-1) + fibonacci(n-2)
    """
    cache = {}
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    
    wrapper.cache = cache
    wrapper.clear_cache = lambda: cache.clear()
    
    return wrapper

