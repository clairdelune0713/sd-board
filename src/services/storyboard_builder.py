import os
from PIL import Image, ImageDraw, ImageFont
from typing import List

class StoryboardBuilder:
    def __init__(self):
        self.width = 2880
        # Height is dynamic now
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
            self.font_subtitle = ImageFont.truetype(font_path, 44)
            self.font_body = ImageFont.truetype(font_path, 32)
            self.font_dialogue = ImageFont.truetype(font_path, 36)
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
        return y

    def _resize_and_pad(self, img: Image.Image, target_width: int, target_height: int) -> Image.Image:
        aspect_img = img.width / img.height
        aspect_target = target_width / target_height
        
        if aspect_img > aspect_target:
            new_width = target_width
            new_height = int(new_width / aspect_img)
        else:
            new_height = target_height
            new_width = int(new_height * aspect_img)
            
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        new_img = Image.new("RGB", (target_width, target_height), (0, 0, 0))
        left = (target_width - new_width) // 2
        top = (target_height - new_height) // 2
        new_img.paste(img, (left, top))
        
        return new_img

    def build_storyboard(
        self,
        frames: List[Image.Image],
        character_images: List[Image.Image],
        movie_idea: str,
        art_style: str,
        environment: str,
        characters: list,
        panel_contexts: List[dict],
        dialogues: List[dict]
    ) -> Image.Image:
        padding = 40
        
        # --- 1. BUILD HEADER DYNAMICALLY ---
        header_canvas = Image.new("RGB", (self.width, 4000), (30, 30, 30))
        header_draw = ImageDraw.Draw(header_canvas)
        
        y = padding
        max_left_width = self.width - padding * 2
        
        y = self._draw_text_wrapped(header_draw, f"Movie Idea: {movie_idea}", (padding, y), self.font_title, max_left_width, fill=self.text_color)
        y += 20
        y = self._draw_text_wrapped(header_draw, f"Art Style: {art_style}", (padding, y), self.font_subtitle, max_left_width, fill=self.accent_color)
        y += 20
        y = self._draw_text_wrapped(header_draw, f"Environment: {environment}", (padding, y), self.font_subtitle, max_left_width, fill=(200, 200, 200))
        y += 40
        
        max_header_y = y
        
        if characters:
            char_size = 300
            total_chars = len(characters)
            header_draw.text((padding, y), "Characters:", font=self.font_subtitle, fill=self.accent_color)
            
            curr_x = padding + 250
            curr_y = y - 20
            
            block_width = (self.width - curr_x - padding) // total_chars if total_chars > 0 else 0
            max_char_y = curr_y + char_size # minimum height
            
            for idx, char_info in enumerate(characters):
                if idx < len(character_images):
                    char_img = character_images[idx]
                    resized_char = self._resize_and_pad(char_img, char_size, char_size)
                    header_canvas.paste(resized_char, (int(curr_x), int(curr_y)))
                
                text_x = curr_x + char_size + 30
                name = char_info.get('name', 'Unknown')
                desc = char_info.get('description', '')
                
                header_draw.text((text_x, curr_y), name, font=self.font_body, fill=self.text_color)
                text_y = self._draw_text_wrapped(header_draw, desc, (text_x, curr_y + 60), self.font_body, block_width - char_size - 50, fill=(200, 200, 200))
                
                max_char_y = max(max_char_y, text_y)
                curr_x += block_width
                
            max_header_y = max_char_y
            
        header_height = max_header_y + padding
        header_canvas = header_canvas.crop((0, 0, self.width, header_height))
        
        # --- 2. BUILD PANELS DYNAMICALLY ---
        panel_width = (self.width - 3 * padding) // 2
        
        aspect_ratio = 9 / 16
        if frames:
            aspect_ratio = frames[0].height / frames[0].width
        image_height = int((panel_width - 8) * aspect_ratio) + 8
        
        built_panels = []
        for i in range(4):
            panel_canvas = Image.new("RGB", (panel_width, 4000), (40, 40, 40))
            panel_draw = ImageDraw.Draw(panel_canvas)
            
            # Place Image
            if i < len(frames):
                frame_img = self._resize_and_pad(frames[i], panel_width - 8, image_height - 8)
                panel_canvas.paste(frame_img, (4, 4))
                
            text_x = 20
            text_y = image_height + 20
            max_text_width = panel_width - 40
            
            panel_data = panel_contexts[i] if i < len(panel_contexts) else {}
            dialogue_data = dialogues[i] if i < len(dialogues) else {}
            
            camera = panel_data.get('camera', 'No camera info')
            action = dialogue_data.get('action', 'No action generated')
            dialogue = dialogue_data.get('dialogue', 'No dialogue generated')
            
            panel_draw.text((text_x, text_y), f"Panel {i+1}", font=self.font_subtitle, fill=self.accent_color)
            text_y += 50
            text_y = self._draw_text_wrapped(panel_draw, f"Camera: {camera}", (text_x, text_y), self.font_body, max_text_width, fill=(150, 255, 150))
            text_y += 10
            text_y = self._draw_text_wrapped(panel_draw, f"Action: {action}", (text_x, text_y), self.font_body, max_text_width, fill=self.text_color)
            text_y += 10
            text_y = self._draw_text_wrapped(panel_draw, f"Dialogue: {dialogue}", (text_x, text_y), self.font_dialogue, max_text_width, fill=(200, 200, 255))
            
            panel_height = text_y + 20
            panel_canvas = panel_canvas.crop((0, 0, panel_width, panel_height))
            
            # Draw outline
            ImageDraw.Draw(panel_canvas).rectangle([0, 0, panel_width - 1, panel_height - 1], outline=(80, 80, 80), width=4)
            
            built_panels.append(panel_canvas)
            
        # --- 3. ASSEMBLE FINAL CANVAS ---
        row1_height = max(built_panels[0].height, built_panels[1].height) if len(built_panels) > 1 else built_panels[0].height
        row2_height = max(built_panels[2].height, built_panels[3].height) if len(built_panels) > 3 else (built_panels[2].height if len(built_panels) > 2 else 0)
        
        final_height = header_height + padding + row1_height + padding + row2_height + padding
        final_canvas = Image.new("RGB", (self.width, final_height), self.bg_color)
        
        final_canvas.paste(header_canvas, (0, 0))
        
        # Row 1
        if len(built_panels) > 0:
            final_canvas.paste(built_panels[0], (padding, header_height + padding))
        if len(built_panels) > 1:
            final_canvas.paste(built_panels[1], (padding * 2 + panel_width, header_height + padding))
            
        # Row 2
        if len(built_panels) > 2:
            final_canvas.paste(built_panels[2], (padding, header_height + padding * 2 + row1_height))
        if len(built_panels) > 3:
            final_canvas.paste(built_panels[3], (padding * 2 + panel_width, header_height + padding * 2 + row1_height))
            
        return final_canvas

storyboard_builder = StoryboardBuilder()
