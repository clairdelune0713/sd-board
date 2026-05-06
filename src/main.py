import argparse
import asyncio
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from io import BytesIO
import uvicorn

import sys
from pathlib import Path

# Add project root to sys.path so 'src' module can be found
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.data_fetcher import data_fetcher
from src.services.dialogue_generator import dialogue_generator
from src.services.storyboard_builder import storyboard_builder
from src.config import config

app = FastAPI(title="SD Board API", description="Generates 4K Storyboards")

class StoryboardRequest(BaseModel):
    user_email: str
    project: str
    storyboard_number: int

async def process_storyboard(req: StoryboardRequest) -> BytesIO:
    # 1. Fetch metadata from Supabase
    db_data = data_fetcher.fetch_storyboard_data(req.user_email, req.project, req.storyboard_number)
    
    movie_idea = db_data['movie_idea']
    art_style = db_data['art_style']
    characters = db_data['characters']
    panels = db_data['panels']
    
    if len(panels) != 4:
        raise ValueError(f"Expected 4 panels, got {len(panels)}")

    bucket = config.S3_BUCKET_R2 if hasattr(config, 'S3_BUCKET_R2') else "aifx-studio"
    if not bucket:
        bucket = "aifx-studio"
    
    loop = asyncio.get_event_loop()

    # 2. Fetch frames from R2
    # aifx-studio/movie-script/{user_email}/{project}/storyboard-{sb_num}-grid-{i}.png
    # Wait, the R2 bucket name in .env is `aifx-studio`. 
    # The path is `movie-script/{user_email}/{project}/...`
    # The user said "aifx-studio/movie-script/..." implying bucket is `aifx-studio` and prefix is `movie-script/...`
    base_prefix = f"movie-script/{req.user_email}/{req.project}"
    
    async def fetch_r2_image(key: str):
        return await loop.run_in_executor(None, data_fetcher.download_image_from_r2, bucket, key)
        
    frame_keys = [f"{base_prefix}/storyboard-{req.storyboard_number}-grid-{i}.png" for i in range(1, 5)]
    try:
        frames = await asyncio.gather(*[fetch_r2_image(key) for key in frame_keys])
    except Exception as e:
        raise ValueError(f"Failed to fetch frames: {e}")

    # 3. Fetch character images from R2 inputs/ folder
    inputs_prefix = f"{base_prefix}/inputs/"
    character_keys = await loop.run_in_executor(None, data_fetcher.list_r2_objects, bucket, inputs_prefix)
    
    character_images = []
    if character_keys:
        try:
            character_images = await asyncio.gather(*[fetch_r2_image(k) for k in character_keys])
        except Exception as e:
            print(f"Warning: Failed to fetch character images: {e}")

    # 4. Generate Dialogue
    dialogues = await dialogue_generator.generate_dialogue(
        movie_idea,
        art_style,
        characters,
        panels
    )

    # 5. Build Storyboard
    canvas = await loop.run_in_executor(
        None,
        storyboard_builder.build_storyboard,
        frames,
        character_images,
        movie_idea,
        art_style,
        characters,
        panels,
        dialogues
    )

    # 4. Save to BytesIO
    output = BytesIO()
    canvas.save(output, format="JPEG", quality=90)
    output.seek(0)
    return output


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
