import os
from PIL import Image, ImageDraw, ImageFont
from typing import List

class StoryboardBuilder:
    def __init__(self):
        self.width = 3840
        self.height = 2160
        self.bg_color = (20, 20, 20)  # Dark background
        self.text_color = (240, 240, 240)
        self.accent_color = (100, 150, 255)
        
        # Try to load a nice font, fallback to default
        try:
            # Common path for Arial on macOS
            font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
            if not os.path.exists(font_path):
                font_path = "/Library/Fonts/Arial.ttf"
            
            self.font_title = ImageFont.truetype(font_path, 64)
            self.font_subtitle = ImageFont.truetype(font_path, 48)
            self.font_body = ImageFont.truetype(font_path, 36)
            self.font_dialogue = ImageFont.truetype(font_path, 40)
        except Exception:
            # Fallback (will be very small on 4K)
            self.font_title = ImageFont.load_default()
            self.font_subtitle = ImageFont.load_default()
            self.font_body = ImageFont.load_default()
            self.font_dialogue = ImageFont.load_default()

    def _wrap_text(self, text: str, font, max_width: int, draw: ImageDraw.Draw) -> List[str]:
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            line_str = " ".join(current_line)
            # Use textbbox to get width
            bbox = draw.textbbox((0, 0), line_str, font=font)
            w = bbox[2] - bbox[0]
            if w > max_width:
                if len(current_line) == 1:
                    lines.append(current_line[0])
                    current_line = []
                else:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
        
        if current_line:
            lines.append(" ".join(current_line))
            
        return lines

    def _draw_text_wrapped(self, draw: ImageDraw.Draw, text: str, position: tuple, font, max_width: int, fill: tuple):
        x, y = position
        lines = self._wrap_text(text, font, max_width, draw)
        for line in lines:
            draw.text((x, y), line, font=font, fill=fill)
            bbox = draw.textbbox((0, 0), line, font=font)
            y += (bbox[3] - bbox[1]) + 10 # line height + padding
        return y # return next available y

    def _resize_and_crop(self, img: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """Resize and crop image to fill the target dimensions (cover)."""
        aspect_img = img.width / img.height
        aspect_target = target_width / target_height
        
        if aspect_img > aspect_target:
            # Image is wider than target
            new_height = target_height
            new_width = int(new_height * aspect_img)
        else:
            # Image is taller than target
            new_width = target_width
            new_height = int(new_width / aspect_img)
            
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Center crop
        left = (new_width - target_width) / 2
        top = (new_height - target_height) / 2
        right = (new_width + target_width) / 2
        bottom = (new_height + target_height) / 2
        
        return img.crop((left, top, right, bottom))

    def build_storyboard(
        self,
        frames: List[Image.Image],
        movie_idea: str,
        art_style: str,
        characters: str,
        panel_contexts: List[str],
        dialogues: List[str]
    ) -> Image.Image:
        """Assembles the 4K storyboard."""
        canvas = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(canvas)
        
        # 1. Draw Header
        header_height = 250
        padding = 40
        draw.rectangle([0, 0, self.width, header_height], fill=(30, 30, 30))
        
        y = padding
        draw.text((padding, y), f"Movie Idea: {movie_idea}", font=self.font_title, fill=self.text_color)
        y += 80
        draw.text((padding, y), f"Art Style: {art_style}   |   Characters: {characters}", font=self.font_subtitle, fill=self.accent_color)
        
        # 2. Draw Panels (2x2 Grid)
        panel_width = (self.width - 3 * padding) // 2
        panel_height = (self.height - header_height - 3 * padding) // 2
        
        image_height = int(panel_height * 0.75)
        text_height = panel_height - image_height
        
        positions = [
            (padding, header_height + padding), # Top-Left
            (padding * 2 + panel_width, header_height + padding), # Top-Right
            (padding, header_height + padding * 2 + panel_height), # Bottom-Left
            (padding * 2 + panel_width, header_height + padding * 2 + panel_height) # Bottom-Right
        ]
        
        for i in range(4):
            x, y_start = positions[i]
            
            # Draw Panel Background
            draw.rectangle([x, y_start, x + panel_width, y_start + panel_height], fill=(40, 40, 40), outline=(80, 80, 80), width=4)
            
            # Place Image
            if i < len(frames):
                frame_img = self._resize_and_crop(frames[i], panel_width - 8, image_height - 8)
                canvas.paste(frame_img, (x + 4, y_start + 4))
            
            # Place Text
            text_x = x + 20
            text_y = y_start + image_height + 20
            max_text_width = panel_width - 40
            
            # Text payload now contains dicts with camera, action, dialogue
            panel_data = panel_contexts[i] if i < len(panel_contexts) else {}
            
            camera = panel_data.get('camera', 'No camera info')
            action = panel_data.get('action', 'No action info')
            dialogue = dialogues[i] if i < len(dialogues) else ""
            
            draw.text((text_x, text_y), f"Panel {i+1}", font=self.font_subtitle, fill=self.accent_color)
            text_y += 50
            text_y = self._draw_text_wrapped(draw, f"Camera: {camera}", (text_x, text_y), self.font_body, max_text_width, fill=(150, 255, 150))
            text_y += 10
            text_y = self._draw_text_wrapped(draw, f"Action: {action}", (text_x, text_y), self.font_body, max_text_width, fill=self.text_color)
            text_y += 10
            self._draw_text_wrapped(draw, f"Dialogue: {dialogue}", (text_x, text_y), self.font_dialogue, max_text_width, fill=(200, 200, 255))

        return canvas

storyboard_builder = StoryboardBuilder()
