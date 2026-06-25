"""
utils/retry.py - A generic async retry framework.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger("retry_framework")

def async_retry(max_retries: int = 3, initial_backoff: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator for async functions that implements exponential backoff.
    
    Args:
        max_retries: Maximum number of times to retry before raising.
        initial_backoff: Initial sleep duration in seconds. Doubles on each retry.
        exceptions: Tuple of exception classes to catch and retry on.
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            backoff = initial_backoff
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"[{func.__name__}] Failed after {max_retries} retries: {e}")
                        raise
                    
                    logger.warning(f"[{func.__name__}] Attempt {retries}/{max_retries} failed: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
        return wrapper
    return decorator
