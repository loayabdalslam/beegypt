"""
Configuration settings for the AI Code Agent.
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# AI Provider Configuration
# Google/Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")

# Selected AI Provider
SELECTED_PROVIDER = os.getenv("SELECTED_PROVIDER", "gemini").lower()  # Options: gemini, openai, azure-openai, anthropic

# Rate Limiting Configuration
REQUESTS_PER_BATCH = int(os.getenv("REQUESTS_PER_BATCH", "10"))  # Number of requests before adding a delay
BATCH_DELAY_SECONDS = float(os.getenv("BATCH_DELAY_SECONDS", "5.0"))  # Delay in seconds after each batch
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))  # Maximum number of retries for rate-limited requests
INITIAL_RETRY_DELAY = float(os.getenv("INITIAL_RETRY_DELAY", "2.0"))  # Initial delay before retrying

# Timeout Configuration
API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "30.0"))  # Default API timeout in seconds
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "30000"))  # Gemini API timeout in milliseconds
CONNECTION_TIMEOUT = float(os.getenv("CONNECTION_TIMEOUT", "10.0"))  # Connection timeout in seconds
READ_TIMEOUT = float(os.getenv("READ_TIMEOUT", "60.0"))  # Read timeout in seconds

# Multimodal Configuration
ENABLE_MULTIMODAL = os.getenv("ENABLE_MULTIMODAL", "True").lower() in ["true", "1", "yes"]  # Enable multimodal features
MULTIMODAL_PROVIDER = os.getenv("MULTIMODAL_PROVIDER", "openai").lower()  # Provider for multimodal features
MULTIMODAL_MODEL = os.getenv("MULTIMODAL_MODEL", "gpt-4-vision-preview")  # Model for multimodal features

# Retry Configuration
OPERATION_MAX_RETRIES = int(os.getenv("OPERATION_MAX_RETRIES", "5"))  # Maximum retries for operations
OPERATION_RETRY_DELAY = float(os.getenv("OPERATION_RETRY_DELAY", "1.0"))  # Initial delay between operation retries
OPERATION_BACKOFF_FACTOR = float(os.getenv("OPERATION_BACKOFF_FACTOR", "2.0"))  # Backoff factor for operation retries

# Agent Configuration
DEFAULT_TEMPERATURE = 0.2  # Lower temperature for more deterministic outputs
MAX_OUTPUT_TOKENS = 8192  # Maximum tokens for generated responses
PLANNING_TEMPERATURE = 0.4  # Slightly higher temperature for creative planning

# Git Configuration
DEFAULT_BRANCH = "main"
COMMIT_MESSAGE_PREFIX = "[BEE-AI-AGENT]"

# Paths
ROOT_DIR = Path(__file__).parent
OUTPUT_DIR = ROOT_DIR / "output"  # Default output directory
TEMPLATES_DIR = ROOT_DIR / "templates"
SCREENSHOTS_DIR = ROOT_DIR / "screenshots"  # Directory for screenshots

# Screenshot Configuration
ENABLE_SCREENSHOTS = os.getenv("ENABLE_SCREENSHOTS", "True").lower() in ["true", "1", "yes"]  # Enable screenshots
SCREENSHOT_INTERVAL = float(os.getenv("SCREENSHOT_INTERVAL", "5.0"))  # Interval between screenshots during monitoring
SCREENSHOT_MONITOR_DURATION = int(os.getenv("SCREENSHOT_MONITOR_DURATION", "60"))  # Duration to monitor in seconds

# Output path from environment or default
CUSTOM_OUTPUT_PATH = os.getenv("OUTPUT_PATH")
if CUSTOM_OUTPUT_PATH:
    OUTPUT_DIR = Path(CUSTOM_OUTPUT_PATH)
else:
    # Always use the output directory by default
    OUTPUT_DIR = ROOT_DIR / "output"

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True, parents=True)
