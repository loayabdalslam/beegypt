"""
Client for interacting with the Gemini API.
"""
import logging
import asyncio
from typing import Dict, Optional

try:
    import google.generativeai as genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from models.base_client import BaseAIClient
from agent.rate_limiter import RateLimiter
from config import GOOGLE_API_KEY, GEMINI_MODEL, DEFAULT_TEMPERATURE, MAX_OUTPUT_TOKENS, \
    REQUESTS_PER_BATCH, BATCH_DELAY_SECONDS, MAX_RETRIES, INITIAL_RETRY_DELAY, \
    API_TIMEOUT_SECONDS, GEMINI_TIMEOUT_MS, CONNECTION_TIMEOUT, READ_TIMEOUT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiClient(BaseAIClient):
    """Client for interacting with Google's Gemini API."""

    # Create a rate limiter instance
    _rate_limiter = RateLimiter(
        requests_per_batch=REQUESTS_PER_BATCH,
        batch_delay_seconds=BATCH_DELAY_SECONDS,
        max_retries=MAX_RETRIES,
        initial_retry_delay=INITIAL_RETRY_DELAY
    )

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Gemini client with timeout configuration.

        Args:
            api_key: Google API key for Gemini
            model: Gemini model to use
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Generative AI package is not installed. Install it with 'pip install google-generativeai'")

        self.api_key = api_key or GOOGLE_API_KEY
        self.model = model or GEMINI_MODEL
        self.timeout_seconds = API_TIMEOUT_SECONDS

        if not self.api_key:
            raise ValueError("Google API key is required. Set it in .env file or pass it to the constructor.")

        # Configure the Gemini API with timeout settings
        genai.configure(api_key=self.api_key)

        # Initialize client with HttpOptions for timeout configuration
        try:
            self.genai_client = genai.Client(
                http_options=types.HttpOptions(
                    timeout=GEMINI_TIMEOUT_MS  # timeout in milliseconds
                )
            )
            logger.info(f"Gemini client initialized with {GEMINI_TIMEOUT_MS}ms timeout")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini client with HttpOptions, falling back to default: {e}")
            self.genai_client = None

        # Get the model
        try:
            self.gemini_model = genai.GenerativeModel(
                model_name=self.model,
                generation_config={
                    "temperature": DEFAULT_TEMPERATURE,
                    "max_output_tokens": MAX_OUTPUT_TOKENS,
                }
            )
            logger.info(f"Successfully initialized Gemini model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise

    async def _execute_with_timeout(self, func, *args, **kwargs):
        """
        Execute a function with timeout using asyncio.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            asyncio.TimeoutError: If function execution exceeds timeout
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(func, *args, **kwargs),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Gemini API request timed out after {self.timeout_seconds} seconds")
            raise RuntimeError(f"Gemini API request timed out after {self.timeout_seconds} seconds")
        except Exception as e:
            logger.error(f"Error in timeout wrapper: {e}")
            raise

    def _execute_with_sync_timeout(self, func, *args, **kwargs):
        """
        Execute a function with timeout using asyncio in sync context.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self._execute_with_timeout(func, *args, **kwargs)
                )
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in sync timeout wrapper: {e}")
            raise

    def generate_text(self, prompt: str, temperature: Optional[float] = None) -> str:
        """
        Generate text using the Gemini model with timeout handling.

        Args:
            prompt: The prompt to send to the model
            temperature: Temperature for generation (0.0 to 1.0)

        Returns:
            Generated text response
        """
        try:
            # Set temperature if provided
            generation_config = None
            if temperature is not None:
                generation_config = {"temperature": temperature}

            # Add the base prompt (bee philosophy + calm instruction) to the prompt
            prompt_with_instruction = prompt + self.BASE_PROMPT

            # Log the prompt for debugging
            logger.debug(f"Sending prompt to Gemini (length: {len(prompt_with_instruction)}):\n{prompt_with_instruction[:500]}...")

            # Define a function to make the API call with timeout
            def make_api_call():
                try:
                    # Use new client with HttpOptions if available
                    if self.genai_client:
                        return self.genai_client.models.generate_content(
                            model=self.model,
                            contents=prompt_with_instruction
                        )
                    else:
                        # Fallback to original method
                        return self.gemini_model.generate_content(
                            prompt_with_instruction,
                            generation_config=generation_config
                        )
                except Exception as e:
                    logger.error(f"API call failed: {e}")
                    raise

            # Generate response with rate limiting, retries, and timeout
            logger.info(f"Making Gemini API request with rate limiting and {self.timeout_seconds}s timeout")
            
            # Execute with timeout wrapper
            response = self._execute_with_sync_timeout(
                lambda: self._rate_limiter.execute_with_rate_limit(make_api_call)
            )

            # Log the response for debugging
            response_text = response.text
            logger.debug(f"Received response from Gemini (length: {len(response_text)}):\n{response_text[:500]}...")

            if not response_text or len(response_text.strip()) < 10:
                logger.warning(f"Received very short or empty response from Gemini: '{response_text}'")

            return response_text
        except Exception as e:
            error_msg = f"Error generating text: {str(e)}"
            logger.error(error_msg)
            # Raise the exception instead of returning an error string
            # This allows the calling code to handle the error appropriately
            raise RuntimeError(error_msg) from e

    def generate_code(self, prompt: str, language: str = "python") -> str:
        """
        Generate code using the Gemini model with optimized settings for code.

        Args:
            prompt: The prompt describing the code to generate
            language: The programming language to generate code for

        Returns:
            Generated code
        """
        code_prompt = f"""
        Generate {language} code for the following task:

        {prompt}

        Provide only the code without explanations. Ensure the code is complete, well-structured, and follows best practices.
        """

        try:
            # Add the base prompt (bee philosophy + calm instruction) to the prompt
            code_prompt_with_instruction = code_prompt + self.BASE_PROMPT

            # Log the prompt for debugging
            logger.debug(f"Sending code prompt to Gemini (language: {language}, length: {len(code_prompt_with_instruction)}):\n{code_prompt_with_instruction[:500]}...")

            # Define a function to make the API call with timeout
            def make_api_call():
                try:
                    # Use new client with HttpOptions if available
                    if self.genai_client:
                        return self.genai_client.models.generate_content(
                            model=self.model,
                            contents=code_prompt_with_instruction
                        )
                    else:
                        # Fallback to original method
                        return self.gemini_model.generate_content(
                            code_prompt_with_instruction,
                            generation_config={
                                "temperature": 0.1,  # Lower temperature for more deterministic code
                            }
                        )
                except Exception as e:
                    logger.error(f"Code generation API call failed: {e}")
                    raise

            # Generate response with rate limiting, retries, and timeout
            logger.info(f"Making Gemini API request for code generation with rate limiting and {self.timeout_seconds}s timeout")
            
            # Execute with timeout wrapper
            response = self._execute_with_sync_timeout(
                lambda: self._rate_limiter.execute_with_rate_limit(make_api_call)
            )

            # Log the response for debugging
            response_text = response.text
            logger.debug(f"Received code response from Gemini (length: {len(response_text)}):\n{response_text[:500]}...")

            if not response_text or len(response_text.strip()) < 10:
                logger.warning(f"Received very short or empty code response from Gemini: '{response_text}'")

            return response_text
        except Exception as e:
            error_msg = f"Error generating code: {str(e)}"
            logger.error(error_msg)
            # Raise the exception instead of returning an error string
            raise RuntimeError(error_msg) from e

    def analyze_code(self, code: str) -> Dict:
        """
        Analyze code for quality, issues, and suggestions.

        Args:
            code: The code to analyze

        Returns:
            Dictionary with analysis results
        """
        analysis_prompt = f"""
        Analyze the following code for quality, potential issues, and suggestions for improvement:

        ```
        {code}
        ```

        Provide your analysis in the following JSON format:
        {{
            "issues": [
                {{
                    "severity": "high/medium/low",
                    "description": "Description of the issue",
                    "line": "line number or range",
                    "suggestion": "Suggested fix"
                }}
            ],
            "quality_score": "1-10",
            "suggestions": [
                "Suggestion 1",
                "Suggestion 2"
            ]
        }}

        Return ONLY the JSON without any additional text or explanation.

        """
        
        # Add the base prompt (bee philosophy + calm instruction)
        analysis_prompt += self.BASE_PROMPT

        try:
            # Log the prompt for debugging
            logger.debug(f"Sending analysis prompt to Gemini (code length: {len(code)}):\n{analysis_prompt[:500]}...")

            # Define a function to make the API call with timeout
            def make_api_call():
                try:
                    # Use new client with HttpOptions if available
                    if self.genai_client:
                        return self.genai_client.models.generate_content(
                            model=self.model,
                            contents=analysis_prompt
                        )
                    else:
                        # Fallback to original method
                        return self.gemini_model.generate_content(analysis_prompt)
                except Exception as e:
                    logger.error(f"Code analysis API call failed: {e}")
                    raise

            # Generate response with rate limiting, retries, and timeout
            logger.info(f"Making Gemini API request for code analysis with rate limiting and {self.timeout_seconds}s timeout")
            
            # Execute with timeout wrapper
            response = self._execute_with_sync_timeout(
                lambda: self._rate_limiter.execute_with_rate_limit(make_api_call)
            )
            response_text = response.text

            # Log the response for debugging
            logger.debug(f"Received analysis response from Gemini (length: {len(response_text)}):\n{response_text[:500]}...")

            # Try to parse the response as JSON
            try:
                import json
                # Find JSON in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    analysis_json = json.loads(json_str)
                    return analysis_json
                else:
                    # If no JSON found, return the raw text
                    return {"analysis": response_text}
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw text
                return {"analysis": response_text}
        except Exception as e:
            error_msg = f"Error analyzing code: {str(e)}"
            logger.error(error_msg)
            # Return an error dictionary instead of raising an exception
            # This is because code analysis is not critical to the main workflow
            return {"error": error_msg}
