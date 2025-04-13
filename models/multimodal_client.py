"""
Multimodal AI client interface for the AI Code Agent.
Extends the base AI client to support image inputs.
"""
import base64
import logging
import os
from abc import abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union

from models.base_client import BaseAIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultimodalAIClient(BaseAIClient):
    """Base class for multimodal AI clients that support image inputs."""
    
    def __init__(self):
        """Initialize the multimodal AI client."""
        super().__init__()
    
    @abstractmethod
    def analyze_image(self, image_path: Union[str, Path], prompt: str) -> Dict:
        """
        Analyze an image with a text prompt.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt to guide the analysis
            
        Returns:
            Dictionary with analysis results
        """
        pass
    
    @abstractmethod
    def generate_from_image(self, image_path: Union[str, Path], prompt: str) -> Dict:
        """
        Generate content based on an image and a text prompt.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt to guide the generation
            
        Returns:
            Dictionary with generated content
        """
        pass
    
    def encode_image_to_base64(self, image_path: Union[str, Path]) -> str:
        """
        Encode an image to base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64-encoded image string
        """
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_error_screenshot(self, screenshot_path: Union[str, Path]) -> Dict:
        """
        Analyze a screenshot for errors.
        
        Args:
            screenshot_path: Path to the screenshot
            
        Returns:
            Dictionary with analysis results and suggested fixes
        """
        prompt = """
        Analyze this screenshot for errors or issues. 
        
        If you find any errors:
        1. Identify the type of error
        2. Explain the likely cause
        3. Suggest specific fixes
        
        Focus on:
        - Error messages in terminals or consoles
        - UI rendering issues
        - Missing elements
        - Unexpected behaviors
        
        Format your response as a structured analysis with sections for:
        - Error identification
        - Cause analysis
        - Suggested fixes (with code if applicable)
        """
        
        return self.analyze_image(screenshot_path, prompt)
    
    def suggest_code_fix_from_error(self, screenshot_path: Union[str, Path], code_context: str) -> Dict:
        """
        Suggest code fixes based on an error screenshot and code context.
        
        Args:
            screenshot_path: Path to the error screenshot
            code_context: Current code context
            
        Returns:
            Dictionary with suggested fixes
        """
        prompt = f"""
        This screenshot shows an error that occurred when running the following code:
        
        ```
        {code_context}
        ```
        
        Please:
        1. Identify the error shown in the screenshot
        2. Explain what's causing the error
        3. Provide a corrected version of the code that fixes the issue
        
        Format your response with clear sections for the error identification, explanation, and the corrected code.
        """
        
        return self.generate_from_image(screenshot_path, prompt)
    
    def analyze_ui_screenshot(self, screenshot_path: Union[str, Path], requirements: str) -> Dict:
        """
        Analyze a UI screenshot against requirements.
        
        Args:
            screenshot_path: Path to the UI screenshot
            requirements: UI requirements to check against
            
        Returns:
            Dictionary with analysis results
        """
        prompt = f"""
        Analyze this UI screenshot against the following requirements:
        
        {requirements}
        
        Please:
        1. Identify which requirements are met
        2. Identify which requirements are not met
        3. Suggest improvements to meet all requirements
        
        Format your response with clear sections for met requirements, unmet requirements, and suggested improvements.
        """
        
        return self.analyze_image(screenshot_path, prompt)
