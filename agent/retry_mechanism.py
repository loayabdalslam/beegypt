"""
Retry mechanism for the AI Code Agent.
Handles automatic retries for failed operations.
"""
import logging
import time
from functools import wraps
from typing import Callable, Dict, Any, Optional, List, Tuple

from agent.screenshot_utils import ScreenshotManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RetryManager:
    """
    Manages retries for failed operations.
    """
    
    def __init__(self, max_retries: int = 5, initial_delay: float = 1.0, backoff_factor: float = 2.0):
        """
        Initialize the retry manager.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            backoff_factor: Factor to increase delay with each retry
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.screenshot_manager = ScreenshotManager()
        
    def with_retry(self, func: Callable, *args, **kwargs) -> Tuple[bool, Any, int]:
        """
        Execute a function with automatic retries.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Tuple of (success, result, attempts)
        """
        attempts = 0
        current_delay = self.initial_delay
        
        while attempts < self.max_retries:
            attempts += 1
            
            try:
                # Execute the function
                logger.info(f"Attempt {attempts}/{self.max_retries}: Executing {func.__name__}")
                result = func(*args, **kwargs)
                
                # Check if the result indicates success
                if isinstance(result, dict) and "success" in result:
                    if result["success"]:
                        logger.info(f"Operation {func.__name__} succeeded on attempt {attempts}")
                        return True, result, attempts
                    else:
                        logger.warning(f"Operation {func.__name__} failed on attempt {attempts}: {result.get('error', 'Unknown error')}")
                elif isinstance(result, bool):
                    if result:
                        logger.info(f"Operation {func.__name__} succeeded on attempt {attempts}")
                        return True, result, attempts
                    else:
                        logger.warning(f"Operation {func.__name__} failed on attempt {attempts}")
                else:
                    # Assume success if we can't determine
                    logger.info(f"Operation {func.__name__} completed on attempt {attempts} (success assumed)")
                    return True, result, attempts
                
                # Take a screenshot to analyze for errors
                screenshot_result = self.screenshot_manager.capture_and_analyze(f"{func.__name__}_attempt_{attempts}")
                
                if screenshot_result["success"] and screenshot_result["has_errors"]:
                    logger.warning(f"Errors detected in screenshot after attempt {attempts}")
                    for error in screenshot_result["errors"]:
                        logger.warning(f"Error pattern: {error['pattern']}")
                        logger.warning(f"Error context: {error['context']}")
                
            except Exception as e:
                logger.error(f"Exception in {func.__name__} on attempt {attempts}: {e}")
                
                # Take a screenshot to analyze for errors
                self.screenshot_manager.capture_screenshot(f"{func.__name__}_exception_{attempts}")
            
            # If we've reached the maximum number of retries, break
            if attempts >= self.max_retries:
                logger.error(f"Maximum retries ({self.max_retries}) reached for {func.__name__}")
                break
            
            # Wait before the next retry
            logger.info(f"Waiting {current_delay:.2f} seconds before retry {attempts + 1}")
            time.sleep(current_delay)
            
            # Increase the delay for the next retry
            current_delay *= self.backoff_factor
        
        # If we get here, all retries failed
        return False, None, attempts
    
    def retry_decorator(self, max_retries: Optional[int] = None, capture_screenshot: bool = True):
        """
        Decorator for functions that should be retried on failure.
        
        Args:
            max_retries: Maximum number of retry attempts (overrides instance default)
            capture_screenshot: Whether to capture screenshots on failure
            
        Returns:
            Decorated function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                local_max_retries = max_retries if max_retries is not None else self.max_retries
                attempts = 0
                current_delay = self.initial_delay
                
                while attempts < local_max_retries:
                    attempts += 1
                    
                    try:
                        # Execute the function
                        logger.info(f"Attempt {attempts}/{local_max_retries}: Executing {func.__name__}")
                        result = func(*args, **kwargs)
                        
                        # Check if the result indicates success
                        if isinstance(result, dict) and "success" in result:
                            if result["success"]:
                                logger.info(f"Operation {func.__name__} succeeded on attempt {attempts}")
                                return result
                            else:
                                logger.warning(f"Operation {func.__name__} failed on attempt {attempts}: {result.get('error', 'Unknown error')}")
                        elif isinstance(result, bool):
                            if result:
                                logger.info(f"Operation {func.__name__} succeeded on attempt {attempts}")
                                return result
                            else:
                                logger.warning(f"Operation {func.__name__} failed on attempt {attempts}")
                        else:
                            # Assume success if we can't determine
                            logger.info(f"Operation {func.__name__} completed on attempt {attempts} (success assumed)")
                            return result
                        
                        # Take a screenshot to analyze for errors if requested
                        if capture_screenshot:
                            screenshot_result = self.screenshot_manager.capture_and_analyze(f"{func.__name__}_attempt_{attempts}")
                            
                            if screenshot_result["success"] and screenshot_result["has_errors"]:
                                logger.warning(f"Errors detected in screenshot after attempt {attempts}")
                                for error in screenshot_result["errors"]:
                                    logger.warning(f"Error pattern: {error['pattern']}")
                                    logger.warning(f"Error context: {error['context']}")
                        
                    except Exception as e:
                        logger.error(f"Exception in {func.__name__} on attempt {attempts}: {e}")
                        
                        # Take a screenshot to analyze for errors if requested
                        if capture_screenshot:
                            self.screenshot_manager.capture_screenshot(f"{func.__name__}_exception_{attempts}")
                    
                    # If we've reached the maximum number of retries, break
                    if attempts >= local_max_retries:
                        logger.error(f"Maximum retries ({local_max_retries}) reached for {func.__name__}")
                        break
                    
                    # Wait before the next retry
                    logger.info(f"Waiting {current_delay:.2f} seconds before retry {attempts + 1}")
                    time.sleep(current_delay)
                    
                    # Increase the delay for the next retry
                    current_delay *= self.backoff_factor
                
                # If we get here, all retries failed
                return {"success": False, "error": f"Failed after {attempts} attempts", "function": func.__name__}
            
            return wrapper
        
        return decorator
