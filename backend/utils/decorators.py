"""
Utility Decorators for Best Practices
- Retry logic with exponential backoff
- Rate limiting
- Validation
- Error handling
- Performance monitoring
"""
import functools
import time
import asyncio
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
import structlog

from constants import (
    MAX_RETRIES,
    RETRY_DELAY,
    RETRY_BACKOFF,
    REQUEST_TIMEOUT,
    ErrorMessages
)

logger = structlog.get_logger()


def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    initial_delay: float = RETRY_DELAY,
    backoff: float = RETRY_BACKOFF,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        
    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        async def fetch_data():
            return await api.call()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e)
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error(
                            "max_retries_exceeded",
                            function=func.__name__,
                            max_retries=max_retries,
                            error=str(e)
                        )
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e)
                        )
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error(
                            "max_retries_exceeded",
                            function=func.__name__,
                            max_retries=max_retries,
                            error=str(e)
                        )
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def timeout(seconds: int = REQUEST_TIMEOUT):
    """
    Timeout decorator for async functions
    
    Args:
        seconds: Timeout in seconds
        
    Example:
        @timeout(120)
        async def long_running_task():
            await some_operation()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                logger.error(
                    "function_timeout",
                    function=func.__name__,
                    timeout=seconds
                )
                raise TimeoutError(
                    ErrorMessages.API_TIMEOUT.format(timeout=seconds)
                )
        
        return wrapper
    return decorator


def validate_input(**validators):
    """
    Input validation decorator
    
    Args:
        **validators: Dictionary of parameter_name: validation_function
        
    Example:
        def validate_description(desc: str) -> bool:
            return 20 <= len(desc) <= 5000
            
        @validate_input(description=validate_description)
        async def process(description: str):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Validate kwargs
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        logger.error(
                            "validation_failed",
                            function=func.__name__,
                            parameter=param_name,
                            value=str(value)[:100]
                        )
                        raise ValueError(f"Validation failed for parameter: {param_name}")
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        logger.error(
                            "validation_failed",
                            function=func.__name__,
                            parameter=param_name,
                            value=str(value)[:100]
                        )
                        raise ValueError(f"Validation failed for parameter: {param_name}")
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_execution_time(log_level: str = "info"):
    """
    Log function execution time
    
    Args:
        log_level: Logging level (info, debug, warning)
        
    Example:
        @log_execution_time(log_level="debug")
        async def process_data():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                log_func = getattr(logger, log_level, logger.info)
                log_func(
                    "function_executed",
                    function=func.__name__,
                    execution_time=f"{execution_time:.2f}s"
                )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    execution_time=f"{execution_time:.2f}s",
                    error=str(e)
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                log_func = getattr(logger, log_level, logger.info)
                log_func(
                    "function_executed",
                    function=func.__name__,
                    execution_time=f"{execution_time:.2f}s"
                )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    execution_time=f"{execution_time:.2f}s",
                    error=str(e)
                )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


class RateLimiter:
    """
    Rate limiter for API calls
    
    Example:
        rate_limiter = RateLimiter(calls=60, period=60)
        
        @rate_limiter.limit
        async def api_call():
            pass
    """
    
    def __init__(self, calls: int, period: int):
        """
        Args:
            calls: Maximum number of calls
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.call_times: list[datetime] = []
    
    def _clean_old_calls(self):
        """Remove call times older than the period"""
        cutoff = datetime.now() - timedelta(seconds=self.period)
        self.call_times = [t for t in self.call_times if t > cutoff]
    
    def limit(self, func: Callable) -> Callable:
        """Rate limit decorator"""
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            self._clean_old_calls()
            
            if len(self.call_times) >= self.calls:
                wait_time = (self.call_times[0] + timedelta(seconds=self.period) - datetime.now()).total_seconds()
                if wait_time > 0:
                    logger.warning(
                        "rate_limit_exceeded",
                        function=func.__name__,
                        wait_time=f"{wait_time:.2f}s"
                    )
                    raise Exception(
                        ErrorMessages.RATE_LIMIT_EXCEEDED.format(seconds=int(wait_time) + 1)
                    )
            
            self.call_times.append(datetime.now())
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            self._clean_old_calls()
            
            if len(self.call_times) >= self.calls:
                wait_time = (self.call_times[0] + timedelta(seconds=self.period) - datetime.now()).total_seconds()
                if wait_time > 0:
                    logger.warning(
                        "rate_limit_exceeded",
                        function=func.__name__,
                        wait_time=f"{wait_time:.2f}s"
                    )
                    raise Exception(
                        ErrorMessages.RATE_LIMIT_EXCEEDED.format(seconds=int(wait_time) + 1)
                    )
            
            self.call_times.append(datetime.now())
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


def handle_errors(default_return: Any = None, log_traceback: bool = True):
    """
    Error handling decorator with optional default return value
    
    Args:
        default_return: Value to return on error
        log_traceback: Whether to log full traceback
        
    Example:
        @handle_errors(default_return={}, log_traceback=True)
        async def risky_operation():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    "error_handled",
                    function=func.__name__,
                    error=str(e),
                    traceback=log_traceback
                )
                return default_return
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    "error_handled",
                    function=func.__name__,
                    error=str(e),
                    traceback=log_traceback
                )
                return default_return
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

