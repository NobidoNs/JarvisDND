from datetime import datetime
from typing import Dict, List, Optional

from services.ai_client import StableAIClient
from services.image_service import record_image
from utils.local_storage import JsonStore, next_id
from utils.prompt_utils import get_system_prompt, get_user_prompt, enhance_image_prompt

_session_store = JsonStore("chat_sessions", default_factory=list)
_message_store = JsonStore("chat_messages", default_factory=list)


class ChatService:
    def __init__(self, ai_client: Optional[StableAIClient] = None):
        self.ai_client = ai_client or StableAIClient()

    def process_chat_message(
        self,
        *,
        user_id: str,
        message: str,
        selected_prompts: Optional[List[Dict]] = None,
        session_id: Optional[int] = None,
        model: Optional[str] = None,
    ) -> Dict:
        """Process chat message and generate AI response."""

        session = self._get_or_create_session(user_id, session_id, message)
        ai_response = self._generate_ai_response(message, selected_prompts, session["id"], model)
        self._persist_messages(session["id"], user_id, message, ai_response)
        images = self._generate_chat_images(user_id, message, ai_response, selected_prompts)
        return {"response": ai_response, "session_id": session["id"], **images}

    def list_chat_sessions(self, user_id: str) -> List[Dict]:
        sessions = [s for s in _session_store.read() if s.get("user_id") == user_id]
        messages = _message_store.read()
        result = []
        for session in sessions:
            session_messages = [
                msg for msg in messages if msg.get("session_id") == session.get("id")
            ]
            session_messages.sort(key=lambda m: m.get("created_at", ""))
            last_message = session_messages[-1]["content"] if session_messages else None
            result.append(
                {
                    "id": session.get("id"),
                    "session_name": session.get("session_name"),
                    "updated_at": session.get("updated_at"),
                    "last_message": (last_message[:100] if last_message else None),
                }
            )
        return sorted(result, key=lambda s: s.get("updated_at", ""), reverse=True)

    def get_session_messages(self, session_id: int, user_id: str) -> List[Dict]:
        session = self._find_session(session_id, user_id)
        if not session:
            return []
        messages = [
            msg
            for msg in _message_store.read()
            if msg.get("session_id") == session_id
        ]
        messages.sort(key=lambda msg: msg.get("created_at", ""))
        return messages

    def delete_chat_session(self, session_id: int, user_id: str) -> bool:
        sessions = _session_store.read()
        new_sessions = [
            s for s in sessions if not (s.get("id") == session_id and s.get("user_id") == user_id)
        ]
        if len(new_sessions) == len(sessions):
            return False
        _session_store.write(new_sessions)

        messages = _message_store.read()
        messages = [m for m in messages if m.get("session_id") != session_id]
        _message_store.write(messages)
        return True

    def _get_or_create_session(self, user_id: str, session_id: Optional[int], message: str) -> Dict:
        sessions = _session_store.read()
        session = None
        if session_id:
            session = next(
                (s for s in sessions if s.get("id") == session_id and s.get("user_id") == user_id),
                None,
            )
        if not session:
            session = {
                "id": next_id(sessions),
                "user_id": user_id,
                "session_name": (message[:50] if message else "New session"),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            sessions.append(session)
        else:
            session["session_name"] = session.get("session_name") or (message[:50] if message else "Chat")
            session["updated_at"] = datetime.utcnow().isoformat()
        _session_store.write(sessions)
        return session

    def _find_session(self, session_id: int, user_id: str) -> Optional[Dict]:
        sessions = _session_store.read()
        for session in sessions:
            if session.get("id") == session_id and session.get("user_id") == user_id:
                return session
        return None

    def _persist_messages(self, session_id: int, user_id: str, user_message: str, ai_response: str) -> None:
        messages = _message_store.read()
        user_record = {
            "id": next_id(messages),
            "session_id": session_id,
            "user_id": user_id,
            "role": "user",
            "content": user_message,
            "created_at": datetime.utcnow().isoformat(),
        }
        messages.append(user_record)
        ai_record = {
            "id": next_id(messages),
            "session_id": session_id,
            "user_id": user_id,
            "role": "assistant",
            "content": ai_response,
            "created_at": datetime.utcnow().isoformat(),
        }
        messages.append(ai_record)
        _message_store.write(messages)

    def _generate_ai_response(
        self,
        message: str,
        selected_prompts: Optional[List[Dict]],
        session_id: int,
        model: Optional[str],
    ) -> str:
        system_message = get_system_prompt()
        user_prompt = get_user_prompt()
        combined_prompt = f"{system_message}\n\n{user_prompt}"

        if selected_prompts:
            prompt_contents = [p.get("content", "") for p in selected_prompts if p.get("content")]
            if prompt_contents:
                combined_prompt += f"\n\nVery important context: {' '.join(prompt_contents)}"

        conversation = [{"role": "system", "content": combined_prompt}]

        history = [
            msg
            for msg in _message_store.read()
            if msg.get("session_id") == session_id
        ]
        history.sort(key=lambda msg: msg.get("created_at", ""))
        for msg in history:
            conversation.append({"role": msg.get("role"), "content": msg.get("content")})

        conversation.append({"role": "user", "content": message})

        return self.ai_client.chat_completion(
            messages=conversation,
            model=(model or "gpt-4"),
            temperature=0.7,
            max_tokens=1000,
        )

    def _generate_chat_images(
        self,
        user_id: str,
        user_message: str,
        ai_response: str,
        selected_prompts: Optional[List[Dict]],
    ) -> Dict:
        try:
            user_image_prompt = enhance_image_prompt(user_message, selected_prompts)
            user_image_response = self.ai_client.generate_image(
                model="sdxl-1.0",
                prompt=user_image_prompt,
                response_format="url",
            )
            user_image_url = user_image_response.data[0].url
            record_image(user_id, user_image_url, user_message[:500], "chat")

            ai_image_prompt = enhance_image_prompt(
                f"{ai_response}", selected_prompts
            )
            ai_image_response = self.ai_client.generate_image(
                model="sdxl-1.0",
                prompt=ai_image_prompt,
                response_format="url",
            )
            ai_image_url = ai_image_response.data[0].url
            record_image(user_id, ai_image_url, f"ИИ: {user_message}"[:500], "chat")

            return {
                "user_image_url": user_image_url,
                "ai_image_url": ai_image_url,
            }
        except Exception as exc:
            print(f"Image generation error: {exc}")
            return {}

