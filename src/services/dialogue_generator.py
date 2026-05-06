import json
import google.generativeai as genai
from typing import List
from src.config import config

class DialogueGenerator:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        # Use gemini-3-flash-preview as requested
        self.model = genai.GenerativeModel('gemini-3-flash-preview')

    async def generate_dialogue(
        self,
        movie_idea: str,
        art_style: str,
        characters: list,
        panel_contexts: List[dict]
    ) -> List[dict]:
        """
        Generates action and dialogue for 4 panels based on the provided inputs.
        Returns a list of 4 dicts: {'action': '...', 'dialogue': '...'}
        """
        char_descriptions = "\\n".join([f"{c.get('name', 'Unknown')}: {c.get('description', '')}" for c in characters])
        
        prompt = f"""
        You are a storyboard director and dialogue writer. 
        Based on the following movie idea, art style, and character descriptions, 
        please generate concise `action` and `dialogue` for {len(panel_contexts)} storyboard panels.
        
        Movie Idea: {movie_idea}
        Art Style: {art_style}
        Characters:
        {char_descriptions}
        
        Here is the raw content for the {len(panel_contexts)} panels:
        """
        
        for i, context in enumerate(panel_contexts):
            raw_content = context.get('raw_content', '')
            prompt += f"\\nPanel {i + 1} Content: {raw_content}"
            
        prompt += """
        
        Output strictly in JSON array format containing exactly 4 objects. Do not use markdown code blocks like ```json. Just output the raw JSON array.
        Format:
        [
            {"action": "Concise summary of what is happening visibly...", "dialogue": "Character Name: 'The exact spoken line.'"},
            {"action": "...", "dialogue": "..."},
            {"action": "...", "dialogue": "..."},
            {"action": "...", "dialogue": "..."}
        ]
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
                
            data = json.loads(text.strip())
            
            # Ensure we return exactly the same number of items as panels
            while len(data) < len(panel_contexts):
                data.append({"action": "Action missing", "dialogue": ""})
            return data[:len(panel_contexts)]
        except Exception as e:
            print(f"Error generating dialogue: {e}")
            return [{"action": p.get("raw_content", ""), "dialogue": "(Failed to generate dialogue)"} for p in panel_contexts]

dialogue_generator = DialogueGenerator()
