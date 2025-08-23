"""
Base client for AI providers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseAIClient(ABC):
    """Abstract base class for AI provider clients."""

    # Base prompt inspired by the bee philosophy
    BEE_BASE_PROMPT = "\n\nBe like the bee, it eats good things, produces good things, and when it lands on a branch, it does not break it, and when it lands on a flower, it does not scratch it."
    
    # Common instruction to add to all prompts
    CALM_INSTRUCTION = "\n\nIMPORTANT: You have to take the answer that came to you and do not rush the matter, do not rush the response and do not rush your algorithms. Take your time and answer very calmly."
    
    # Combined base prompt with bee philosophy and calm instruction
    BASE_PROMPT = BEE_BASE_PROMPT + CALM_INSTRUCTION

    @abstractmethod
    def generate_text(self, prompt: str, temperature: Optional[float] = None) -> str:
        """
        Generate text using the AI model.

        Args:
            prompt: The prompt to send to the model
            temperature: Temperature for generation (0.0 to 1.0)

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def generate_code(self, prompt: str, language: str = "python") -> str:
        """
        Generate code using the AI model.

        Args:
            prompt: The prompt describing the code to generate
            language: The programming language to generate code for

        Returns:
            Generated code
        """
        pass

    @abstractmethod
    def analyze_code(self, code: str) -> Dict:
        """
        Analyze code for quality, issues, and suggestions.

        Args:
            code: The code to analyze

        Returns:
            Dictionary with analysis results
        """
        pass
