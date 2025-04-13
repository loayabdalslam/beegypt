"""
Multimodal OpenAI client for the AI Code Agent.
Extends the OpenAI client to support image inputs.
"""
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import openai
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL, DEFAULT_TEMPERATURE, MAX_OUTPUT_TOKENS, \
    REQUESTS_PER_BATCH, BATCH_DELAY_SECONDS, MAX_RETRIES, INITIAL_RETRY_DELAY
from models.multimodal_client import MultimodalAIClient
from agent.rate_limiter import RateLimiter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultimodalOpenAIClient(MultimodalAIClient):
    """OpenAI client with multimodal capabilities."""
    
    # Create a rate limiter instance
    _rate_limiter = RateLimiter(
        requests_per_batch=REQUESTS_PER_BATCH,
        batch_delay_seconds=BATCH_DELAY_SECONDS,
        max_retries=MAX_RETRIES,
        initial_retry_delay=INITIAL_RETRY_DELAY
    )
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the multimodal OpenAI client.
        
        Args:
            api_key: OpenAI API key (default: from config)
            model: OpenAI model to use (default: from config)
        """
        super().__init__()
        
        # Use provided values or defaults from config
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or "gpt-4-vision-preview"  # Use vision model by default
        
        # Initialize the OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"Initialized MultimodalOpenAIClient with model: {self.model}")
    
    def generate_response(self, prompt: str, temp: float = DEFAULT_TEMPERATURE) -> Dict:
        """
        Generate a response to a text prompt.
        
        Args:
            prompt: Text prompt
            temp: Temperature for generation
            
        Returns:
            Dictionary with generated response
        """
        try:
            # Log the prompt for debugging
            logger.debug(f"Sending prompt to OpenAI (length: {len(prompt)}):\\n{prompt[:500]}...")
            
            # Add the calm instruction to the prompt
            prompt_with_instruction = prompt + self.CALM_INSTRUCTION
            
            # Define a function to make the API call
            def make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt_with_instruction}],
                    temperature=temp,
                    max_tokens=MAX_OUTPUT_TOKENS
                )
            
            # Use the rate limiter to make the API call
            response = self._rate_limiter.execute_with_rate_limit(make_api_call)
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            return {
                "success": True,
                "response": response_text
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_image(self, image_path: Union[str, Path], prompt: str) -> Dict:
        """
        Analyze an image with a text prompt.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt to guide the analysis
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Convert to Path object
            image_path = Path(image_path)
            
            # Check if the image exists
            if not image_path.exists():
                return {
                    "success": False,
                    "error": f"Image not found: {image_path}"
                }
            
            # Log the request
            logger.info(f"Analyzing image: {image_path}")
            logger.debug(f"Prompt: {prompt[:500]}...")
            
            # Add the calm instruction to the prompt
            prompt_with_instruction = prompt + self.CALM_INSTRUCTION
            
            # Define a function to make the API call
            def make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_with_instruction},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{self.encode_image_to_base64(image_path)}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=MAX_OUTPUT_TOKENS
                )
            
            # Use the rate limiter to make the API call
            response = self._rate_limiter.execute_with_rate_limit(make_api_call)
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            return {
                "success": True,
                "analysis": response_text,
                "image_path": str(image_path)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_path": str(image_path) if 'image_path' in locals() else None
            }
    
    def generate_from_image(self, image_path: Union[str, Path], prompt: str) -> Dict:
        """
        Generate content based on an image and a text prompt.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt to guide the generation
            
        Returns:
            Dictionary with generated content
        """
        try:
            # Convert to Path object
            image_path = Path(image_path)
            
            # Check if the image exists
            if not image_path.exists():
                return {
                    "success": False,
                    "error": f"Image not found: {image_path}"
                }
            
            # Log the request
            logger.info(f"Generating content from image: {image_path}")
            logger.debug(f"Prompt: {prompt[:500]}...")
            
            # Add the calm instruction to the prompt
            prompt_with_instruction = prompt + self.CALM_INSTRUCTION
            
            # Define a function to make the API call
            def make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_with_instruction},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{self.encode_image_to_base64(image_path)}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=MAX_OUTPUT_TOKENS
                )
            
            # Use the rate limiter to make the API call
            response = self._rate_limiter.execute_with_rate_limit(make_api_call)
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            return {
                "success": True,
                "generated_content": response_text,
                "image_path": str(image_path)
            }
            
        except Exception as e:
            logger.error(f"Error generating from image: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_path": str(image_path) if 'image_path' in locals() else None
            }
    
    def generate_code(self, prompt: str, language: str = "python") -> Dict:
        """
        Generate code based on a text prompt.
        
        Args:
            prompt: Text prompt
            language: Programming language
            
        Returns:
            Dictionary with generated code
        """
        try:
            # Create a code generation prompt
            code_prompt = f"""
            Generate {language} code for the following task:
            
            {prompt}
            
            Provide only the code without explanations. Ensure the code is complete, well-structured, and follows best practices.
            
            IMPORTANT: You have to take the answer that came to you and do not rush the matter, do not rush the response and do not rush your algorithms. Take your time and answer very calmly.
            """
            
            # Log the prompt for debugging
            logger.debug(f"Sending code prompt to OpenAI (language: {language}, length: {len(code_prompt)}):\\n{code_prompt[:500]}...")
            
            # Define a function to make the API call
            def make_api_call():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": code_prompt}],
                    temperature=0.1,  # Lower temperature for more deterministic code
                    max_tokens=MAX_OUTPUT_TOKENS
                )
            
            # Use the rate limiter to make the API call
            response = self._rate_limiter.execute_with_rate_limit(make_api_call)
            
            # Extract the response text
            code = response.choices[0].message.content
            
            return {
                "success": True,
                "code": code,
                "language": language
            }
            
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return {
                "success": False,
                "error": str(e)
            }
