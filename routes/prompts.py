from flask import Blueprint, jsonify, request

from services.prompt_service import PromptService
from utils.local_user import get_user_id

prompts_bp = Blueprint("prompts", __name__, url_prefix="/api")
prompt_service = PromptService()


@prompts_bp.route("/prompts", methods=["GET"])
def get_prompts():
    prompts = prompt_service.get_user_prompts(get_user_id())
    return jsonify(prompts)


@prompts_bp.route("/prompts", methods=["POST"])
def create_prompt():
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title or not content:
        return jsonify({"error": "Prompt title and content are required."}), 400
    prompt = prompt_service.create_prompt(
        user_id=get_user_id(),
        title=title,
        content=content,
    )
    return jsonify(prompt), 201


@prompts_bp.route("/prompts/<int:prompt_id>", methods=["PUT"])
def update_prompt(prompt_id):
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title or not content:
        return jsonify({"error": "Prompt title and content are required."}), 400
    prompt = prompt_service.update_prompt(
        prompt_id=prompt_id,
        user_id=get_user_id(),
        title=title,
        content=content,
    )
    if prompt:
        return jsonify(prompt)
    return "", 404


@prompts_bp.route("/prompts/<int:prompt_id>", methods=["DELETE"])
def delete_prompt(prompt_id):
    success = prompt_service.delete_prompt(prompt_id, get_user_id())
    if success:
        return "", 204
    return "", 404