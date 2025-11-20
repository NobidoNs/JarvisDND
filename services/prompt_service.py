from datetime import datetime
from typing import Dict, List, Optional

from utils.local_storage import JsonStore, next_id

_prompt_store = JsonStore("prompts", default_factory=list)


class PromptService:
    def __init__(self, store: JsonStore = _prompt_store):
        self.store = store

    def get_user_prompts(self, user_id: str) -> List[Dict]:
        """Return all prompts for the local user sorted by creation date."""

        prompts = [p for p in self.store.read() if p.get("user_id") == user_id]
        return sorted(prompts, key=lambda p: p.get("created_at", ""), reverse=True)

    def create_prompt(self, user_id: str, title: str, content: str) -> Dict:
        """Create and persist a prompt."""

        prompts = self.store.read()
        prompt = {
            "id": next_id(prompts),
            "user_id": user_id,
            "title": title,
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
        }
        prompts.append(prompt)
        self.store.write(prompts)
        return prompt

    def update_prompt(self, prompt_id: int, user_id: str, title: str, content: str) -> Optional[Dict]:
        """Update an existing prompt."""

        prompts = self.store.read()
        updated = None
        for prompt in prompts:
            if prompt.get("id") == prompt_id and prompt.get("user_id") == user_id:
                prompt["title"] = title
                prompt["content"] = content
                updated = prompt
                break
        if updated:
            self.store.write(prompts)
        return updated

    def delete_prompt(self, prompt_id: int, user_id: str) -> bool:
        """Delete a prompt by id."""

        prompts = self.store.read()
        new_prompts = [p for p in prompts if not (p.get("id") == prompt_id and p.get("user_id") == user_id)]
        if len(new_prompts) != len(prompts):
            self.store.write(new_prompts)
            return True
        return False

    def get_prompt_by_id(self, prompt_id: int, user_id: str) -> Optional[Dict]:
        """Retrieve a single prompt."""

        prompts = self.store.read()
        for prompt in prompts:
            if prompt.get("id") == prompt_id and prompt.get("user_id") == user_id:
                return prompt
        return None