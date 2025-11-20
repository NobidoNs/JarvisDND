from datetime import datetime
from typing import Dict, List, Optional

from services.ai_client import StableAIClient
from utils.local_storage import JsonStore, next_id
from utils.prompt_utils import get_system_prompt

_images_store = JsonStore("images", default_factory=list)


def record_image(user_id: str, url: str, prompt: str, source: str) -> Dict:
    """Persist a generated image and return the stored record."""

    images = _images_store.read()
    record = {
        "id": next_id(images),
        "user_id": user_id,
        "url": url,
        "prompt": prompt,
        "source": source,
        "created_at": datetime.utcnow().isoformat(),
    }
    images.append(record)
    _images_store.write(images)
    return record


class ImageService:
    def __init__(self, ai_client: Optional[StableAIClient] = None):
        self.ai_client = ai_client or StableAIClient()

    def generate_image(self, user_id: str, prompt: str) -> Dict[str, List[str]]:
        """Generate and store four images for a prompt."""

        enhanced_prompt = self._enhance_prompt(prompt)
        image_urls: List[str] = []
        for _ in range(4):
            response = self.ai_client.generate_image(
                model="sdxl-1.0",
                prompt=enhanced_prompt,
                response_format="url",
            )
            image_url = response.data[0].url
            image_urls.append(image_url)
            record_image(user_id, image_url, enhanced_prompt, "image_generator")
        return {"image_urls": image_urls}

    def list_images(self, user_id: str) -> List[Dict]:
        images = [img for img in _images_store.read() if img.get("user_id") == user_id]
        return sorted(images, key=lambda img: img.get("created_at", ""), reverse=True)

    def update_image(self, image_id: int, user_id: str, prompt: str) -> Optional[Dict]:
        images = _images_store.read()
        updated = None
        for image in images:
            if image.get("id") == image_id and image.get("user_id") == user_id:
                image["prompt"] = prompt
                image["updated_at"] = datetime.utcnow().isoformat()
                updated = image
                break
        if updated:
            _images_store.write(images)
        return updated

    def delete_image(self, image_id: int, user_id: str) -> bool:
        images = _images_store.read()
        new_images = [img for img in images if not (img.get("id") == image_id and img.get("user_id") == user_id)]
        if len(new_images) != len(images):
            _images_store.write(new_images)
            return True
        return False

    def _enhance_prompt(self, prompt: str) -> str:
        """Enhance prompt with D&D context."""

        system_context = get_system_prompt()
        if "D&D" in system_context or "Dungeons and Dragons" in system_context:
            return f"Dungeons and Dragons themed scene, fantasy RPG style: {prompt}"
        return prompt