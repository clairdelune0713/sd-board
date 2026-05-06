import json
from google import genai
from typing import List
from src.config import config

class DialogueGenerator:
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = 'gemini-3-flash-preview'

    async def generate_dialogue(
        self,
        frames: list,
        movie_idea: str,
        art_style: str,
        characters: list,
        panel_contexts: List[dict]
    ) -> dict:
        """
        Generates action, dialogue, and environment description based on images and context.
        Returns a dict: {'environment': '...', 'panels': [{'action': '...', 'dialogue': '...'}]}
        """
        char_descriptions = "\\n".join([f"{c.get('name', 'Unknown')}: {c.get('description', '')}" for c in characters])
        
        prompt = f"""
        You are a storyboard director and dialogue writer. 
        Based on the attached 4 frames, the movie idea, art style, and character descriptions, 
        please generate:
        1. A detailed `environment` description that summarizes the setting based purely on what you see in the images.
        2. Concise `action` and `dialogue` for each of the {len(panel_contexts)} panels.
        
        Movie Idea: {movie_idea}
        Art Style: {art_style}
        Characters:
        {char_descriptions}
        
        Here is the raw context for the {len(panel_contexts)} panels:
        """
        
        for i, context in enumerate(panel_contexts):
            raw_content = context.get('raw_content', '')
            prompt += f"\\nPanel {i + 1} Content: {raw_content}"
            
        prompt += """
        
        Output strictly in JSON format containing an object. Do not use markdown code blocks like ```json.
        Format:
        {
            "environment": "Detailed description of the setting and visual atmosphere seen in the images...",
            "panels": [
                {"action": "Concise summary...", "dialogue": "Character Name: 'Spoken line.'"},
                {"action": "...", "dialogue": "..."},
                {"action": "...", "dialogue": "..."},
                {"action": "...", "dialogue": "..."}
            ]
        }
        """
        
        try:
            # We pass the prompt and the 4 images to Gemini
            content_parts = [prompt] + frames
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=content_parts
            )
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
                
            data = json.loads(text.strip())
            
            # Ensure panels matches
            panels = data.get("panels", [])
            while len(panels) < len(panel_contexts):
                panels.append({"action": "Action missing", "dialogue": ""})
            data["panels"] = panels[:len(panel_contexts)]
            return data
            
        except Exception as e:
            print(f"Error generating dialogue: {e}")
            return {
                "environment": "(Failed to generate environment)",
                "panels": [{"action": p.get("raw_content", ""), "dialogue": "(Failed to generate dialogue)"} for p in panel_contexts]
            }

dialogue_generator = DialogueGenerator()
