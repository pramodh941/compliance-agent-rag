"""
Simple retry decorator for external service calls.

Provides exponential backoff retry logic without external dependencies.
"""
import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)


def retry_on_exception(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None,
    operation_name: Optional[str] = None
):
    """
    Decorator to retry a function on specific exceptions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry on
        on_retry: Optional callback function called on each retry
        operation_name: Optional name for logging/tracing visibility
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            op_name = operation_name or func.__name__
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"Operation '{op_name}' failed after {max_retries} retries",
                            extra={
                                "operation": op_name,
                                "max_retries": max_retries,
                                "final_error": str(e),
                                "retry_exhausted": True
                            }
                        )
                        raise
                    
                    # Calculate exponential backoff delay
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    logger.warning(
                        f"Operation '{op_name}' failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.2f}s",
                        extra={
                            "operation": op_name,
                            "attempt": attempt + 1,
                            "max_retries": max_retries + 1,
                            "retry_delay_s": round(delay, 2),
                            "error": str(e)
                        }
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator
