from flask import Blueprint, jsonify, request

from services.chat_service import ChatService
from utils.local_user import get_user_id

chat_bp = Blueprint("chat", __name__, url_prefix="/api")
chat_service = ChatService()


@chat_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    selected_prompts = data.get("selected_prompts", [])
    session_id = data.get("session_id")
    model = data.get("model")

    if not message:
        return jsonify({"error": "No message provided"}), 400

    try:
        result = chat_service.process_chat_message(
            user_id=get_user_id(),
            message=message,
            selected_prompts=selected_prompts,
            session_id=session_id,
            model=model,
        )
        return jsonify(result)
    except Exception as exc:
        print(f"Chat error: {exc}")
        return jsonify({"error": "Failed to generate response. Please try again."}), 500


@chat_bp.route("/chat-history", methods=["GET"])
def chat_history():
    history = chat_service.list_chat_sessions(get_user_id())
    return jsonify(history)


@chat_bp.route("/chat-history/<int:session_id>", methods=["GET"])
def chat_history_session(session_id):
    messages = chat_service.get_session_messages(session_id, get_user_id())
    return jsonify(messages)


@chat_bp.route("/chat-history/<int:session_id>", methods=["DELETE"])
def delete_chat_session(session_id):
    if chat_service.delete_chat_session(session_id, get_user_id()):
        return "", 204
    return "", 404