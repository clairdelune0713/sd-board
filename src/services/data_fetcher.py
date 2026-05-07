import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from io import BytesIO
from PIL import Image
import httpx
import psycopg2
import psycopg2.extras
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
        self.db_url = config.DATABASE_URL.replace("?pgbouncer=true", "")

    def get_db_connection(self):
        """Returns a new psycopg2 connection to Supabase."""
        return psycopg2.connect(self.db_url)

    def fetch_storyboard_data(self, user_email: str, project_id: str, storyboard_number: int):
        """
        Fetches the storyboard metadata (movie_idea, art_style, characters) 
        and the 4 panel contexts from Supabase.
        """
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 1. Fetch project info
                cur.execute(
                    "SELECT movie_idea, art_style, characters, non_characters FROM cinedual_projects WHERE user_email = %s AND session_timestamp = %s",
                    (user_email, project_id)
                )
                proj = cur.fetchone()
                if not proj:
                    raise ValueError(f"Project not found for {user_email} and {project_id}")
                
                movie_idea = proj['movie_idea']
                art_style = proj['art_style']
                
                # Keep full character list for detailed display
                chars_list = proj['characters'] or []
                
                # Extract non_characters as environment details
                non_chars_list = proj['non_characters'] or []
                env_str = ", ".join([c.get('name', 'Unknown') for c in non_chars_list]) if non_chars_list else "Not specified"
                
                # 2. Fetch panels context (camera info)
                cur.execute(
                    "SELECT panel, angle, content FROM scenes_content WHERE user_email = %s AND project_id = %s AND scene = %s AND panel IS NOT NULL AND name NOT LIKE '%%-original' ORDER BY panel LIMIT 4",
                    (user_email, project_id, storyboard_number)
                )
                panels_db = cur.fetchall()
                
                # 3. Fetch actions and dialogues
                cur.execute(
                    "SELECT panel, action_text, dialogue_text FROM cine_action_dialogues WHERE user_email = %s AND project_id = %s AND scene = %s ORDER BY panel LIMIT 4",
                    (user_email, project_id, storyboard_number)
                )
                dialogues_db = cur.fetchall()
                dialogue_map = {d['panel']: d for d in dialogues_db}
                
                # Environment description: Use Panel 0's action_text if available
                env_desc = dialogue_map.get(0, {}).get('action_text', env_str)
                
                panels = []
                for p in panels_db:
                    panel_idx = p['panel']
                    d_info = dialogue_map.get(panel_idx, {})
                    panels.append({
                        "camera": p['angle'] or "Unknown Angle",
                        "action": d_info.get('action_text', p['content'] or ""),
                        "dialogue": d_info.get('dialogue_text', "")
                    })
                    
                # 4. Fetch environment info to find the 'i' for env-i.png
                cur.execute(
                    "SELECT scenes, category_index FROM project_environments WHERE user_email = %s AND project_id = %s ORDER BY category_index",
                    (user_email, project_id)
                )
                envs_db = cur.fetchall()
                
                env_index = 1 # Fallback
                for env_row in envs_db:
                    # env_row['scenes'] is an ARRAY of integers
                    if storyboard_number in (env_row['scenes'] or []):
                        # Use category_index (usually 1, 2, 3...) directly for the image name
                        env_index = env_row['category_index'] if env_row['category_index'] is not None else 1
                        break
                
                env_image_key = f"movie-script/{user_email}/{project_id}/boards/env-{env_index}.png"
                    
                return {
                    "movie_idea": movie_idea,
                    "art_style": art_style,
                    "environment": env_desc,
                    "env_image_key": env_image_key,
                    "characters": chars_list,
                    "panels": panels
                }

    def list_r2_objects(self, bucket: str, prefix: str) -> list[str]:
        """Lists object keys in an R2 bucket under a specific prefix."""
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents'] if not obj['Key'].endswith('/')]
            return []
        except Exception as e:
            print(f"Error listing objects in {bucket}/{prefix}: {e}")
            return []

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

    def upload_image_to_r2(self, bucket: str, object_key: str, image_data: bytes, content_type: str = "image/png"):
        """Uploads image data to Cloudflare R2."""
        try:
            self.s3_client.put_object(
                Bucket=bucket,
                Key=object_key,
                Body=image_data,
                ContentType=content_type
            )
            print(f"Successfully uploaded to {bucket}/{object_key}")
        except Exception as e:
            print(f"Error uploading to {bucket}/{object_key}: {e}")
            raise

data_fetcher = DataFetcher()
