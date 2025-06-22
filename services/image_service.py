from g4f.client import Client
from models import db, GeneratedImage
from utils.prompt_utils import get_system_prompt

class ImageService:
    def __init__(self):
        self.client = Client()
    
    def generate_image(self, user_id, prompt):
        """Generate image from prompt"""
        try:
            enhanced_prompt = self._enhance_prompt(prompt)
            
            response = self.client.images.generate(
                model="sdxl-1.0",
                prompt=enhanced_prompt,
                response_format="url"
            )

            # Save generated image to database
            image = GeneratedImage(
                url=response.data[0].url,
                prompt=enhanced_prompt,
                user_id=user_id,
                source='image_generator'
            )
            db.session.add(image)
            db.session.commit()
            
            return {"image_url": response.data[0].url}
            
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            raise
    
    def _enhance_prompt(self, prompt):
        """Enhance prompt with D&D context"""
        system_context = get_system_prompt()
        enhanced_prompt = prompt
        
        # If system prompt contains D&D mentions, add appropriate context
        if "D&D" in system_context or "Dungeons and Dragons" in system_context:
            enhanced_prompt = f"Dungeons and Dragons themed scene, fantasy RPG style: {prompt}"
        
        return enhanced_prompt 