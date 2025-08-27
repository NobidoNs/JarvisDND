from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.chat_service import ChatService
from models import ChatSession, ChatMessage

chat_bp = Blueprint('chat', __name__, url_prefix='/api')
chat_service = ChatService()

@chat_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    message = data.get('message')
    selected_prompts = data.get('selected_prompts', [])
    session_id = data.get('session_id')
    model = data.get('model')
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        result = chat_service.process_chat_message(
            user_id=current_user.id,
            message=message,
            selected_prompts=selected_prompts,
            session_id=session_id,
            model=model
        )
        return jsonify(result)
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return jsonify({"error": "Failed to generate response. Please try again."}), 500

@chat_bp.route('/chat-history', methods=['GET'])
@login_required
def chat_history():
    sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.updated_at.desc()).all()
    result = []
    for session in sessions:
        last_message = ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.created_at.desc()).first()
        result.append({
            'id': session.id,
            'session_name': session.session_name,
            'updated_at': session.updated_at.isoformat() if session.updated_at else None,
            'last_message': last_message.content[:100] if last_message and last_message.content else None
        })
    return jsonify(result)

@chat_bp.route('/chat-history/<int:session_id>', methods=['GET'])
@login_required
def chat_history_session(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        return jsonify([])
    messages = ChatMessage.query.filter_by(session_id=session.id).order_by(ChatMessage.created_at.asc()).all()
    return jsonify([
        {
            'id': m.id,
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.isoformat()
        } for m in messages
    ])

@chat_bp.route('/chat-history/<int:session_id>', methods=['DELETE'])
@login_required
def delete_chat_session(session_id):
    from models import db
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        return '', 404
    db.session.delete(session)
    db.session.commit()
    return '', 204 