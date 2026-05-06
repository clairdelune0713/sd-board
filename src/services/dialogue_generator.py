import google.generativeai as genai
from typing import List
from src.config import config

class DialogueGenerator:
    def __init__(self):
        genai.configure(api_key=config.GEMINI_API_KEY)
        # Use gemini-pro as fallback
        self.model = genai.GenerativeModel('gemini-pro')

    async def generate_dialogue(
        self,
        movie_idea: str,
        art_style: str,
        characters: str,
        panel_contexts: List[str]
    ) -> List[str]:
        """
        Generates dialogue for 4 panels based on the provided inputs.
        Returns a list of 4 strings, corresponding to the dialogue for each panel.
        """
        prompt = f"""
        You are a storyboard dialogue writer. Based on the following movie idea, art style, and characters, 
        please generate concise dialogue or narration for {len(panel_contexts)} storyboard panels.
        
        Movie Idea: {movie_idea}
        Art Style: {art_style}
        Characters: {characters}
        
        Here are the descriptions (contexts) for the {len(panel_contexts)} panels:
        """
        
        for i, context in enumerate(panel_contexts):
            prompt += f"\nPanel {i + 1} Context: {context}"
            
        prompt += """
        
        Output format: Please output EXACTLY 4 lines (one for each panel).
        Each line should only contain the dialogue or narration for that panel, without numbering.
        For example:
        Character A: "Wow!"
        (Narration) The sun sets.
        Character B: "Let's go."
        Character A: "Okay."
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()
            # Split by newlines and filter out empty lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Ensure we return exactly the same number of lines as panels
            if len(lines) != len(panel_contexts):
                # Fallback if the model didn't follow formatting
                print(f"Warning: Expected {len(panel_contexts)} lines, got {len(lines)}.")
                # Try to pad or truncate
                lines = lines[:len(panel_contexts)]
                while len(lines) < len(panel_contexts):
                    lines.append("(No dialogue)")
                    
            return lines
        except Exception as e:
            print(f"Error generating dialogue: {e}")
            return ["(Dialogue generation failed)"] * len(panel_contexts)

dialogue_generator = DialogueGenerator()
