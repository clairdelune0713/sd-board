import argparse
import asyncio
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from io import BytesIO
import uvicorn
from functools import partial

import sys
from pathlib import Path

# Add project root to sys.path so 'src' module can be found
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.data_fetcher import data_fetcher
from src.services.storyboard_builder import storyboard_builder
from src.config import config

app = FastAPI(title="SD Board API", description="Generates 4K Storyboards")

class StoryboardRequest(BaseModel):
    user_email: str
    project: str
    storyboard_number: int

async def process_storyboard(req: StoryboardRequest) -> BytesIO:
    # 1. Fetch metadata from Supabase
    loop = asyncio.get_event_loop()
    db_data = await loop.run_in_executor(
        None, 
        data_fetcher.fetch_storyboard_data, 
        req.user_email, 
        req.project, 
        req.storyboard_number
    )
    
    movie_idea = db_data['movie_idea']
    art_style = db_data['art_style']
    characters = db_data['characters']
    panels = db_data['panels']
    
    if len(panels) != 4:
        raise ValueError(f"Expected 4 panels, got {len(panels)}")

    bucket = config.S3_BUCKET_R2 if hasattr(config, 'S3_BUCKET_R2') else "aifx-studio"
    if not bucket:
        bucket = "aifx-studio"

    # 2. Fetch frames from R2
    # aifx-studio/movie-script/{user_email}/{project}/storyboard-{sb_num}-grid-{i}.png
    # Wait, the R2 bucket name in .env is `aifx-studio`. 
    # The path is `movie-script/{user_email}/{project}/...`
    # The user said "aifx-studio/movie-script/..." implying bucket is `aifx-studio` and prefix is `movie-script/...`
    base_prefix = f"movie-script/{req.user_email}/{req.project}"
    
    async def fetch_r2_image(key: str):
        return await loop.run_in_executor(None, data_fetcher.download_image_from_r2, bucket, key)
        
    frame_keys = [f"{base_prefix}/boards/board-{req.storyboard_number}-{i}.png" for i in range(1, 5)]
    try:
        frames_task = asyncio.gather(*[fetch_r2_image(key) for key in frame_keys])
        env_image_task = fetch_r2_image(db_data['env_image_key'])
        
        frames, env_image = await asyncio.gather(frames_task, env_image_task)
    except Exception as e:
        raise ValueError(f"Failed to fetch frames or environment image: {e}")

    # 3. Fetch character images from R2 inputs/ folder
    inputs_prefix = f"{base_prefix}/inputs/"
    character_keys = await loop.run_in_executor(None, data_fetcher.list_r2_objects, bucket, inputs_prefix)
    
    character_images = []
    if character_keys:
        try:
            character_images = await asyncio.gather(*[fetch_r2_image(k) for k in character_keys])
        except Exception as e:
            print(f"Warning: Failed to fetch character images: {e}")

    # 4. Use action/dialogue from DB instead of generating with Gemini
    environment = db_data.get("environment", "Unknown Environment")
    dialogues = db_data.get("panels", []) # These now contain action and dialogue from DB

    # 5. Build Storyboard
    canvas = await loop.run_in_executor(
        None,
        storyboard_builder.build_storyboard,
        frames,
        env_image,
        character_images,
        movie_idea,
        art_style,
        environment,
        characters,
        panels,
        dialogues
    )

    # 4. Save to BytesIO for response (JPEG)
    output_jpeg = BytesIO()
    await loop.run_in_executor(None, partial(canvas.save, output_jpeg, format="JPEG", quality=90))
    output_jpeg.seek(0)

    # 5. Save and Upload to R2 (PNG)
    output_png = BytesIO()
    await loop.run_in_executor(None, partial(canvas.save, output_png, format="PNG"))
    png_data = output_png.getvalue()
    
    r2_key = f"movie-script/{req.user_email}/{req.project}/boards/comp-{req.storyboard_number}.png"
    await loop.run_in_executor(None, data_fetcher.upload_image_to_r2, bucket, r2_key, png_data, "image/png")

    # 6. Trigger GDrive Sync
    asyncio.create_task(trigger_gdrive_sync(r2_key))

    return output_jpeg

async def trigger_gdrive_sync(object_key: str):
    """
    Triggers the Cloudflare GDrive Sync worker for the given R2 object key.
    """
    url = config.GDRIVE_SYNC_WORKER_URL
    secret = config.GDRIVE_SYNC_WORKER_SECRET
    
    if not url or not secret:
        print(f"[GDriveSync] Skipping: Missing worker configuration (URL: {!!url}, Secret: {!!secret})")
        return

    print(f"[GDriveSync] Triggering sync for {object_key}...")
    
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"objectKey": object_key},
                headers={"X-Worker-Secret": secret},
                timeout=10.0
            )
            if resp.status_code == 200:
                print(f"[GDriveSync] Success: {resp.json()}")
            else:
                print(f"[GDriveSync] Failed (Status {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"[GDriveSync] Error triggering sync: {e}")


@app.post("/generate-storyboard", responses={200: {"content": {"image/jpeg": {}}}})
async def generate_storyboard_endpoint(req: StoryboardRequest):
    """
    Generate a 4K storyboard image based on provided contexts and frames.
    """
    try:
        image_stream = await process_storyboard(req)
        return Response(content=image_stream.read(), media_type="image/jpeg")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_cli():
    parser = argparse.ArgumentParser(description="Generate 4K Storyboard")
    parser.add_argument("--json", type=str, required=True, help="Path to input JSON file")
    parser.add_argument("--out", type=str, default="storyboard_output.jpg", help="Output file path")
    args = parser.parse_args()

    with open(args.json, "r") as f:
        data = json.load(f)

    req = StoryboardRequest(**data)

    print("Processing storyboard...")
    
    async def main_async():
        try:
            image_stream = await process_storyboard(req)
            with open(args.out, "wb") as f:
                f.write(image_stream.read())
            print(f"Storyboard saved successfully to {args.out}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error: {e}")

    asyncio.run(main_async())

if __name__ == "__main__":
    import sys
    # If run with arguments, use CLI mode, otherwise use FastAPI server
    if len(sys.argv) > 1 and sys.argv[1] != "serve":
        run_cli()
    else:
        uvicorn.run("src.main:app", host="0.0.0.0", port=8005, reload=True)
