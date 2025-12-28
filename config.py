"""Configuration settings for AI Banker"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Database configuration
DATABASE_PATH = BASE_DIR / "data" / "ai_banker.db"

# AI Configuration
USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Local model configuration (Ollama)
LOCAL_MODEL_URL = os.getenv("LOCAL_MODEL_URL", "http://localhost:11434")
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "llama2")

# AI Features
AI_CATEGORIZATION_ENABLED = os.getenv("AI_CATEGORIZATION_ENABLED", "true").lower() == "true"
AI_INSIGHTS_ENABLED = os.getenv("AI_INSIGHTS_ENABLED", "true").lower() == "true"
AI_ANOMALY_DETECTION_ENABLED = os.getenv("AI_ANOMALY_DETECTION_ENABLED", "true").lower() == "true"
AI_FORECASTING_ENABLED = os.getenv("AI_FORECASTING_ENABLED", "true").lower() == "true"
AI_TRANSACTION_VALIDATION_ENABLED = os.getenv("AI_TRANSACTION_VALIDATION_ENABLED", "true").lower() == "true"

# Streamlit configuration
STREAMLIT_THEME = {
    "primaryColor": "#1f77b4",
    "backgroundColor": "#0e1117",
    "secondaryBackgroundColor": "#262730",
    "textColor": "#fafafa",
    "font": "sans serif"
}

