"""
Application configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Model settings
    GEMINI_MODEL: str = "gemini-2.5-pro"
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Which provider to use: "openai" or "gemini"
    LLM_PROVIDER: str = "gemini"
    
    # PDF settings
    MAX_PDF_PAGES: int = 20
    
    # Storage settings
    # Use path relative to this config file (src/.data), not current working directory
    DATA_DIR: Path = Path(__file__).parent / Path(os.getenv("DATA_DIR", ".data"))
    CHROMA_COLLECTION_NAME: str = "documents"
    
    # UI settings
    APP_TITLE: str = "Annual Report Analyser"


config = Config()
