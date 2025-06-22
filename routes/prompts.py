from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.prompt_service import PromptService

prompts_bp = Blueprint('prompts', __name__, url_prefix='/api')

@prompts_bp.route('/prompts', methods=['GET'])
@login_required
def get_prompts():
    prompts = PromptService.get_user_prompts(current_user.id)
    return jsonify([{
        'id': p.id,
        'title': p.title,
        'content': p.content,
        'created_at': p.created_at.isoformat()
    } for p in prompts])

@prompts_bp.route('/prompts', methods=['POST'])
@login_required
def create_prompt():
    data = request.get_json()
    prompt = PromptService.create_prompt(
        user_id=current_user.id,
        title=data['title'],
        content=data['content']
    )
    return jsonify({
        'id': prompt.id,
        'title': prompt.title,
        'content': prompt.content
    })

@prompts_bp.route('/prompts/<int:prompt_id>', methods=['PUT'])
@login_required
def update_prompt(prompt_id):
    data = request.get_json()
    prompt = PromptService.update_prompt(
        prompt_id=prompt_id,
        user_id=current_user.id,
        title=data['title'],
        content=data['content']
    )
    if prompt:
        return jsonify({
            'id': prompt.id,
            'title': prompt.title,
            'content': prompt.content
        })
    return '', 404

@prompts_bp.route('/prompts/<int:prompt_id>', methods=['DELETE'])
@login_required
def delete_prompt(prompt_id):
    success = PromptService.delete_prompt(prompt_id, current_user.id)
    if success:
        return '', 204
    return '', 404 