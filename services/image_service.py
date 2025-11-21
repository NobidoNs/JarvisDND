from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4

import requests

from config import Config
from services.ai_client import StableAIClient
from utils.local_storage import JsonStore, next_id
from utils.prompt_utils import enhance_image_prompt

_images_store = JsonStore("images", default_factory=list)
_image_download_dir = Path(Config.IMAGE_DOWNLOAD_DIR)
_image_download_dir.mkdir(parents=True, exist_ok=True)


def _sanitize_filename_fragment(prompt: str) -> str:
    if not prompt:
        return "image"
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower())
    slug = slug.strip("-")
    return slug[:40] or "image"


def _detect_extension(url: str) -> str:
    parsed = urlparse(url or "")
    suffix = Path(parsed.path).suffix
    if suffix and len(suffix) <= 6:
        return suffix
    return ".jpg"


def _download_image(url: str, prompt: str) -> Optional[str]:
    if not url:
        return None
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        ext = _detect_extension(url)
        filename = (
            f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{uuid4().hex[:8]}_"
            f"{_sanitize_filename_fragment(prompt)}{ext}"
        )
        file_path = _image_download_dir / filename
        with open(file_path, "wb") as fh:
            fh.write(response.content)
        return str(file_path)
    except Exception as exc:
        print(f"Failed to download image from {url}: {exc}")
        return None


def record_image(user_id: str, url: str, prompt: str, source: str) -> Dict:
    """Persist a generated image, download it locally, and return the stored record."""

    images = _images_store.read()
    record = {
        "id": next_id(images),
        "user_id": user_id,
        "url": url,
        "prompt": prompt,
        "source": source,
        "created_at": datetime.utcnow().isoformat(),
    }
    file_path = _download_image(url, prompt)
    if file_path:
        record["file_path"] = file_path
    images.append(record)
    _images_store.write(images)
    return record


class ImageService:
    DEFAULT_IMAGE_COUNT = 4

    def __init__(self, ai_client: Optional[StableAIClient] = None):
        self.ai_client = ai_client or StableAIClient()

    def generate_image(self, user_id: str, prompt: str) -> Dict[str, List[str]]:
        """Generate and store four images for a prompt using ThreadPoolExecutor."""
        
        enhanced_prompt = enhance_image_prompt(prompt)
        print(enhanced_prompt)
        
        def generate_one(_):
            """Generate one image."""
            try:
                response = self.ai_client.generate_image(
                    model="sdxl-1.0",
                    prompt=enhanced_prompt,
                    response_format="url",
                )

                if not getattr(response, "data", None):
                    return None

                image_url = getattr(response.data[0], "url", None) or response.data[0].get("url")
                if not image_url:
                    return None

                record_image(user_id, image_url, enhanced_prompt, "image_generator")
                return image_url
                
            except Exception as e:
                print(f"Error generating image: {e}")
                return None
        
        # Запускаем все задачи параллельно
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Отправляем все задачи и получаем результаты
            results = list(executor.map(generate_one, range(self.DEFAULT_IMAGE_COUNT)))
        
        # Фильтруем None значения
        image_urls = [url for url in results if url is not None]
        
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
