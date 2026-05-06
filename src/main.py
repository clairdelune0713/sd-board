import argparse
import asyncio
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from io import BytesIO
import uvicorn

from src.services.data_fetcher import data_fetcher
from src.services.dialogue_generator import dialogue_generator
from src.services.storyboard_builder import storyboard_builder
from src.config import config

app = FastAPI(title="SD Board API", description="Generates 4K Storyboards")

class PanelInput(BaseModel):
    camera: str
    action: str
    frame_url: str  # Can be a public http URL or an R2 object key

class StoryboardRequest(BaseModel):
    movie_idea: str
    art_style: str
    characters: str
    panels: List[PanelInput]

async def process_storyboard(req: StoryboardRequest) -> BytesIO:
    if len(req.panels) != 4:
        raise ValueError("Exactly 4 panels are required.")

    # 1. Fetch images concurrently
    async def fetch_image(url: str):
        if url.startswith("http://") or url.startswith("https://"):
            return await data_fetcher.download_image_from_url(url)
        else:
            # Assume it's an R2 key in the default bucket
            # Run the synchronous boto3 call in an executor to avoid blocking
            bucket = "aifx-studio"  # Default bucket from .env S3_BUCKET_R2
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                data_fetcher.download_image_from_r2, 
                bucket, 
                url
            )

    try:
        frames = await asyncio.gather(*[fetch_image(p.frame_url) for p in req.panels])
    except Exception as e:
        raise ValueError(f"Failed to fetch images: {e}")

    # 2. Generate Dialogue
    contexts = [{"camera": p.camera, "action": p.action} for p in req.panels]
    dialogues = await dialogue_generator.generate_dialogue(
        req.movie_idea,
        req.art_style,
        req.characters,
        contexts
    )

    # 3. Build Storyboard
    loop = asyncio.get_event_loop()
    canvas = await loop.run_in_executor(
        None,
        storyboard_builder.build_storyboard,
        frames,
        req.movie_idea,
        req.art_style,
        req.characters,
        contexts,
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
