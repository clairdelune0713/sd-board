import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from io import BytesIO
from PIL import Image
import httpx
from src.config import config

class DataFetcher:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=config.S3_ENDPOINT,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            config=BotoConfig(signature_version='s3v4'),
            region_name='auto'
        )

    def download_image_from_r2(self, bucket: str, object_key: str) -> Image.Image:
        """Downloads an image from Cloudflare R2 and returns a PIL Image."""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=object_key)
            image_data = response['Body'].read()
            return Image.open(BytesIO(image_data)).convert("RGB")
        except ClientError as e:
            print(f"Error downloading {object_key} from {bucket}: {e}")
            raise

    async def download_image_from_url(self, url: str) -> Image.Image:
        """Downloads an image from a public URL and returns a PIL Image."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGB")

data_fetcher = DataFetcher()
