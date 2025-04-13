"""
Client for interacting with the Gemini API.
"""
import logging
from typing import Dict, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from models.base_client import BaseAIClient
from agent.rate_limiter import RateLimiter
from config import GOOGLE_API_KEY, GEMINI_MODEL, DEFAULT_TEMPERATURE, MAX_OUTPUT_TOKENS, \
    REQUESTS_PER_BATCH, BATCH_DELAY_SECONDS, MAX_RETRIES, INITIAL_RETRY_DELAY

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
        Initialize the Gemini client.

        Args:
            api_key: Google API key for Gemini
            model: Gemini model to use
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Generative AI package is not installed. Install it with 'pip install google-generativeai'")

        self.api_key = api_key or GOOGLE_API_KEY
        self.model = model or GEMINI_MODEL

        if not self.api_key:
            raise ValueError("Google API key is required. Set it in .env file or pass it to the constructor.")

        # Configure the Gemini API
        genai.configure(api_key=self.api_key)

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

    def generate_text(self, prompt: str, temperature: Optional[float] = None) -> str:
        """
        Generate text using the Gemini model.

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

            # Add the calm instruction to the prompt
            prompt_with_instruction = prompt + self.CALM_INSTRUCTION

            # Log the prompt for debugging
            logger.debug(f"Sending prompt to Gemini (length: {len(prompt_with_instruction)}):\n{prompt_with_instruction[:500]}...")

            # Define a function to make the API call
            def make_api_call():
                return self.gemini_model.generate_content(
                    prompt_with_instruction,
                    generation_config=generation_config
                )

            # Generate response with rate limiting and retries
            logger.info("Making Gemini API request with rate limiting")
            response = self._rate_limiter.execute_with_rate_limit(make_api_call)

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
            # Add the calm instruction to the prompt
            code_prompt_with_instruction = code_prompt + self.CALM_INSTRUCTION

            # Log the prompt for debugging
            logger.debug(f"Sending code prompt to Gemini (language: {language}, length: {len(code_prompt_with_instruction)}):\n{code_prompt_with_instruction[:500]}...")

            # Define a function to make the API call
            def make_api_call():
                return self.gemini_model.generate_content(
                    code_prompt_with_instruction,
                    generation_config={
                        "temperature": 0.1,  # Lower temperature for more deterministic code
                    }
                )

            # Generate response with rate limiting and retries
            logger.info("Making Gemini API request for code generation with rate limiting")
            response = self._rate_limiter.execute_with_rate_limit(make_api_call)

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

        IMPORTANT: You have to take the answer that came to you and do not rush the matter, do not rush the response and do not rush your algorithms. Take your time and answer very calmly.
        """

        try:
            # Log the prompt for debugging
            logger.debug(f"Sending analysis prompt to Gemini (code length: {len(code)}):\n{analysis_prompt[:500]}...")

            # Define a function to make the API call
            def make_api_call():
                return self.gemini_model.generate_content(analysis_prompt)

            # Generate response with rate limiting and retries
            logger.info("Making Gemini API request for code analysis with rate limiting")
            response = self._rate_limiter.execute_with_rate_limit(make_api_call)
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
