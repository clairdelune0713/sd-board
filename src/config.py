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
    S3_BUCKET_R2 = os.getenv("S3_BUCKET_R2", "aifx-studio")
    
    # DB Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # GDrive Sync Worker
    GDRIVE_SYNC_WORKER_URL = os.getenv("GDRIVE_SYNC_WORKER_URL", "")
    GDRIVE_SYNC_WORKER_SECRET = os.getenv("GDRIVE_SYNC_WORKER_SECRET", "")

config = Config()
