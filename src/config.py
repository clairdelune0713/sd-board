import os
from pathlib import Path
from dotenv import load_dotenv

# Load the local .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # R2 configuration
    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
    S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "")
    
    # DB Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "")

config = Config()
