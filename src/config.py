import os
from pathlib import Path
from dotenv import load_dotenv

# Load the .env from ../aifx-studio
env_path = Path(__file__).resolve().parent.parent.parent / "aifx-studio" / ".env"
load_dotenv(dotenv_path=env_path)

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # R2 configuration
    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
    S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "")

config = Config()
