"""
Rate limiter utility for API requests.
Handles rate limiting and retries for API requests.
"""
import logging
import time
from typing import Callable, TypeVar, Any, Optional
import random

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic function return type
T = TypeVar('T')

class RateLimiter:
    """
    Rate limiter for API requests.
    Handles rate limiting and retries for API requests.
    """
    
    def __init__(self, 
                 requests_per_batch: int = 10, 
                 batch_delay_seconds: float = 5.0,
                 max_retries: int = 3,
                 initial_retry_delay: float = 2.0,
                 jitter: float = 0.5):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_batch: Number of requests to allow before adding a delay
            batch_delay_seconds: Delay in seconds after each batch of requests
            max_retries: Maximum number of retries for rate-limited requests
            initial_retry_delay: Initial delay in seconds before retrying
            jitter: Random jitter factor to add to delays (0-1)
        """
        self.requests_per_batch = requests_per_batch
        self.batch_delay_seconds = batch_delay_seconds
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.jitter = jitter
        
        self.request_count = 0
        self.last_request_time = 0
    
    def execute_with_rate_limit(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with rate limiting and retries.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the function
            
        Raises:
            Exception: If the function fails after all retries
        """
        retry_count = 0
        retry_delay = self.initial_retry_delay
        
        while True:
            try:
                # Check if we need to add a delay before this request
                self._maybe_delay_request()
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Increment the request count
                self.request_count += 1
                self.last_request_time = time.time()
                
                return result
                
            except Exception as e:
                # Check if this is a rate limit error (429)
                is_rate_limit = "429" in str(e) or "Too Many Requests" in str(e)
                
                if is_rate_limit and retry_count < self.max_retries:
                    # Calculate delay with exponential backoff and jitter
                    jitter_amount = random.uniform(0, self.jitter * retry_delay)
                    actual_delay = retry_delay + jitter_amount
                    
                    logger.warning(f"Rate limit exceeded. Retrying in {actual_delay:.2f} seconds. ({retry_count + 1}/{self.max_retries})")
                    time.sleep(actual_delay)
                    
                    # Increment retry count and delay for next retry
                    retry_count += 1
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Either not a rate limit error or we've exceeded max retries
                    logger.error(f"Request failed: {e}")
                    raise
    
    def _maybe_delay_request(self):
        """
        Add a delay if we've reached the batch limit.
        """
        if self.request_count >= self.requests_per_batch:
            # Calculate time since last request
            time_since_last = time.time() - self.last_request_time
            
            # If we've made a batch of requests recently, add a delay
            if time_since_last < self.batch_delay_seconds:
                delay_time = self.batch_delay_seconds - time_since_last
                logger.info(f"Rate limiting: Delaying for {delay_time:.2f} seconds after {self.requests_per_batch} requests")
                time.sleep(delay_time)
            
            # Reset the request count
            self.request_count = 0
