"""
Screenshot utilities for the AI Code Agent.
Captures screenshots and analyzes them for errors.
"""
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import pyautogui
import pytesseract
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configure pytesseract path if needed (especially on Windows)
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class ScreenshotManager:
    """
    Manages screenshot capture and analysis.
    """
    
    def __init__(self, screenshots_dir: Optional[Path] = None):
        """
        Initialize the screenshot manager.
        
        Args:
            screenshots_dir: Directory to save screenshots (default: ./screenshots)
        """
        self.screenshots_dir = screenshots_dir or Path("screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Common error patterns to look for in screenshots
        self.error_patterns = [
            "error", "exception", "failed", "failure", "cannot", "unable to", 
            "not found", "undefined", "null", "nan", "invalid", "syntax error",
            "runtime error", "type error", "reference error", "404", "500",
            "connection refused", "timeout", "permission denied"
        ]
        
    def capture_screenshot(self, name: str = None) -> Tuple[bool, Path]:
        """
        Capture a screenshot of the current screen.
        
        Args:
            name: Optional name for the screenshot
            
        Returns:
            Tuple of (success, screenshot_path)
        """
        try:
            # Generate a filename based on timestamp if not provided
            if not name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            else:
                # Ensure the name has a .png extension
                if not name.endswith('.png'):
                    filename = f"{name}.png"
                else:
                    filename = name
            
            # Create the full path
            screenshot_path = self.screenshots_dir / filename
            
            # Capture the screenshot
            screenshot = pyautogui.screenshot()
            screenshot.save(str(screenshot_path))
            
            logger.info(f"Screenshot captured: {screenshot_path}")
            return True, screenshot_path
        
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return False, None
    
    def analyze_screenshot(self, screenshot_path: Path) -> Dict:
        """
        Analyze a screenshot for errors.
        
        Args:
            screenshot_path: Path to the screenshot
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Check if the file exists
            if not screenshot_path.exists():
                return {
                    "success": False,
                    "error": f"Screenshot not found: {screenshot_path}"
                }
            
            # Open the image
            image = Image.open(screenshot_path)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image)
            
            # Look for error patterns
            errors_found = []
            for pattern in self.error_patterns:
                if pattern.lower() in text.lower():
                    # Find the context around the error
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        if pattern.lower() in line.lower():
                            # Get a few lines before and after for context
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = '\n'.join(lines[start:end])
                            errors_found.append({
                                "pattern": pattern,
                                "line": line.strip(),
                                "context": context
                            })
            
            # Return the analysis results
            return {
                "success": True,
                "has_errors": len(errors_found) > 0,
                "errors": errors_found,
                "text": text,
                "screenshot_path": str(screenshot_path)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def capture_and_analyze(self, name: str = None) -> Dict:
        """
        Capture a screenshot and analyze it for errors.
        
        Args:
            name: Optional name for the screenshot
            
        Returns:
            Dictionary with analysis results
        """
        # Capture the screenshot
        success, screenshot_path = self.capture_screenshot(name)
        
        if not success:
            return {
                "success": False,
                "error": "Failed to capture screenshot"
            }
        
        # Analyze the screenshot
        return self.analyze_screenshot(screenshot_path)
    
    def monitor_for_errors(self, interval: int = 5, duration: int = 60) -> List[Dict]:
        """
        Monitor the screen for errors over a period of time.
        
        Args:
            interval: Time between screenshots in seconds
            duration: Total monitoring duration in seconds
            
        Returns:
            List of error reports
        """
        start_time = time.time()
        end_time = start_time + duration
        error_reports = []
        
        while time.time() < end_time:
            # Capture and analyze a screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result = self.capture_and_analyze(f"monitor_{timestamp}")
            
            # Check if errors were found
            if result["success"] and result["has_errors"]:
                error_reports.append(result)
                logger.warning(f"Errors detected in screenshot: {result['screenshot_path']}")
                
                # Log the errors
                for error in result["errors"]:
                    logger.warning(f"Error pattern: {error['pattern']}")
                    logger.warning(f"Error context: {error['context']}")
            
            # Wait for the next interval
            time.sleep(interval)
        
        return error_reports
