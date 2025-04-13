"""
Factory for creating AI clients.
"""
import logging
from typing import Optional

from models.base_client import BaseAIClient
from models.gemini_client import GeminiClient
from models.openai_client import OpenAIClient
from models.azure_openai_client import AzureOpenAIClient
from models.anthropic_client import AnthropicClient
from models.multimodal_client import MultimodalAIClient
from models.multimodal_openai_client import MultimodalOpenAIClient
from agent.rate_limiter import RateLimiter
from config import SELECTED_PROVIDER, REQUESTS_PER_BATCH, BATCH_DELAY_SECONDS, MAX_RETRIES, INITIAL_RETRY_DELAY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIClientFactory:
    """Factory for creating AI clients."""

    # Create a rate limiter instance
    _rate_limiter = RateLimiter(
        requests_per_batch=REQUESTS_PER_BATCH,
        batch_delay_seconds=BATCH_DELAY_SECONDS,
        max_retries=MAX_RETRIES,
        initial_retry_delay=INITIAL_RETRY_DELAY
    )

    @staticmethod
    def create_client(provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None, multimodal: bool = False) -> BaseAIClient:
        """
        Create an AI client based on the provider.

        Args:
            provider: AI provider (gemini, openai, anthropic)
            api_key: API key for the provider
            model: Model to use
            multimodal: Whether to create a multimodal client

        Returns:
            AI client instance (BaseAIClient or MultimodalAIClient)
        """
        # Use the selected provider from config if not specified
        provider = provider or SELECTED_PROVIDER

        try:
            # If multimodal is requested, return a multimodal client if available
            if multimodal:
                if provider == "openai":
                    return MultimodalOpenAIClient(api_key, model)
                else:
                    logger.warning(f"Multimodal not supported for provider: {provider}. Using OpenAI for multimodal.")
                    return MultimodalOpenAIClient(api_key, model)

            # Otherwise, return a standard client
            if provider == "gemini":
                return GeminiClient(api_key, model)
            elif provider == "openai":
                return OpenAIClient(api_key, model)
            elif provider == "azure-openai":
                return AzureOpenAIClient(api_key, None, model)
            elif provider == "anthropic":
                return AnthropicClient(api_key, model)
            else:
                logger.warning(f"Unknown provider: {provider}. Falling back to Gemini.")
                return GeminiClient(api_key, model)
        except ImportError as e:
            # If the selected provider's package is not installed, try to fall back to another provider
            logger.warning(f"Error creating {provider} client: {e}")

            # If multimodal is requested, try to create a multimodal client
            if multimodal:
                try:
                    return MultimodalOpenAIClient(api_key, model)
                except ImportError:
                    logger.warning("Failed to create multimodal client. Falling back to standard client.")
                    multimodal = False

            # Try to create standard clients in order: Gemini, OpenAI, Azure OpenAI, Anthropic
            for fallback_provider in ["gemini", "openai", "azure-openai", "anthropic"]:
                if fallback_provider != provider:
                    try:
                        if fallback_provider == "gemini":
                            return GeminiClient(api_key, model)
                        elif fallback_provider == "openai":
                            return OpenAIClient(api_key, model)
                        elif fallback_provider == "azure-openai":
                            return AzureOpenAIClient(api_key, None, model)
                        elif fallback_provider == "anthropic":
                            return AnthropicClient(api_key, model)
                    except ImportError:
                        continue

            # If all providers fail, raise an error
            raise ImportError("No AI provider packages are installed. Please install at least one of: google-generativeai, openai, anthropic")

    @staticmethod
    def create_multimodal_client(provider: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None) -> MultimodalAIClient:
        """
        Create a multimodal AI client based on the provider.

        Args:
            provider: AI provider (currently only openai supported)
            api_key: API key for the provider
            model: Model to use

        Returns:
            Multimodal AI client instance
        """
        client = AIClientFactory.create_client(provider, api_key, model, multimodal=True)

        # Ensure the client is a MultimodalAIClient
        if not isinstance(client, MultimodalAIClient):
            raise TypeError(f"Expected MultimodalAIClient but got {type(client).__name__}")

        return client
