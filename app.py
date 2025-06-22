from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from oauthlib.oauth2 import WebApplicationClient
import requests
import os
import json
from g4f.client import Client
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Allow OAuth2 over HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database
with app.app_context():
    db.create_all()
    print("Database tables created successfully")

# Google OAuth2 configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://jarvisdnd.onrender.com/login/callback')  # Dynamic redirect URI based on environment

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise ValueError("Missing Google OAuth credentials. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file")

client = WebApplicationClient(GOOGLE_CLIENT_ID)

def get_system_prompt():
    """Read system prompt from prompts/system.txt file"""
    try:
        with open('prompts/system.txt', 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        # Fallback to default system prompt if file not found
        return "You are a helpful D&D assistant. Provide clear and concise answers about D&D rules, lore, and gameplay. Give answers in md format"
    except Exception as e:
        print(f"Error reading system prompt: {e}")
        return "You are a helpful D&D assistant. Provide clear and concise answers about D&D rules, lore, and gameplay. Give answers in md format"

class User(UserMixin, db.Model):
    id = db.Column(db.String(50), primary_key=True)
    email = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    prompts = db.relationship('Prompt', backref='user', lazy=True)
    images = db.relationship('GeneratedImage', backref='user', lazy=True)

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id'), nullable=False)

class GeneratedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id'), nullable=False)
    source = db.Column(db.String(50), default='image_generator')  # 'image_generator' or 'chat'

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id'), nullable=False)
    session_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade='all, delete-orphan')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    user_id = db.Column(db.String(50), db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' или 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
    # Debug logging
    print("=== OAuth Debug Information ===")
    print(f"Environment REDIRECT_URI: {os.getenv('REDIRECT_URI')}")
    print(f"Final REDIRECT_URI value: {REDIRECT_URI}")
    print(f"Request URL: {request.url}")
    print(f"Request Base URL: {request.base_url}")
    print(f"Request Host: {request.host}")
    print("=============================")
    
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=REDIRECT_URI,
        scope=["openid", "email", "profile"],
    )
    print(f"Using redirect URI: {REDIRECT_URI}")  # Debug log
    print(f"Full request URI: {request_uri}")  # Debug log
    return redirect(request_uri)

@app.route('/login/callback')
def callback():
    code = request.args.get("code")
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]
    
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=REDIRECT_URI,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    client.parse_request_body_response(json.dumps(token_response.json()))
    
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        users_name = userinfo_response.json()["given_name"]
        
        user = User.query.filter_by(email=users_email).first()
        if not user:
            user = User(id=str(unique_id), name=users_name, email=users_email)
            db.session.add(user)
            db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
    return "User email not verified by Google.", 400

@app.route('/dashboard')
@login_required
def dashboard():
    prompts = Prompt.query.filter_by(user_id=current_user.id).order_by(Prompt.created_at.desc()).all()
    return render_template('dashboard.html', prompts=prompts)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    message = data.get('message')
    selected_prompts = data.get('selected_prompts', [])
    session_id = data.get('session_id')  # Можно добавить поддержку передачи session_id с фронта
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        # --- Сессия чата ---
        if session_id:
            session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        else:
            # Название сессии — первые 50 символов сообщения пользователя
            session_name = message[:50] if message else None
            session = ChatSession(user_id=current_user.id, session_name=session_name)
            db.session.add(session)
            db.session.commit()
        # Сохраняем сообщение пользователя
        user_msg = ChatMessage(
            session_id=session.id,
            user_id=current_user.id,
            role='user',
            content=message
        )
        db.session.add(user_msg)
        db.session.commit()
        # --- Генерация ответа ---
        system_message = get_system_prompt()
        if selected_prompts:
            prompt_contents = [p.get('content', '') for p in selected_prompts if p.get('content')]
            if prompt_contents:
                system_message += f"\nAdditional context and style: {' '.join(prompt_contents)}"
        print(system_message)
        client = Client()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        if not response.choices:
            return jsonify({"error": "No response generated"}), 500
        ai_response = response.choices[0].message.content
        # Сохраняем ответ ассистента
        ai_msg = ChatMessage(
            session_id=session.id,
            user_id=current_user.id,
            role='assistant',
            content=ai_response
        )
        db.session.add(ai_msg)
        db.session.commit()
        # --- Генерация изображений (без изменений) ---
        user_image_prompt = message
        if selected_prompts:
            prompt_contents = [p.get('content', '') for p in selected_prompts if p.get('content')]
            if prompt_contents:
                combined_prompt = f"Style and details: {' '.join(prompt_contents)}. Dungeons and Dragons scene: {message}"
                user_image_prompt = combined_prompt
        
        # Добавляем контекст из системного промпта для лучшей генерации изображений
        system_context = get_system_prompt()
        if "D&D" in system_context or "Dungeons and Dragons" in system_context:
            user_image_prompt = f"Dungeons and Dragons themed scene, fantasy RPG style: {user_image_prompt}"
        
        user_image_response = client.images.generate(
            model="sdxl-1.0",
            prompt=user_image_prompt,
            response_format="url"
        )
        user_image = GeneratedImage(
            url=user_image_response.data[0].url,
            prompt=user_image_prompt,
            user_id=current_user.id,
            source='chat'
        )
        db.session.add(user_image)
        
        # Генерация изображения для ответа ИИ с учетом системного контекста
        ai_image_prompt = f"Dungeons and Dragons scene: {ai_response}"
        if selected_prompts:
            prompt_contents = [p.get('content', '') for p in selected_prompts if p.get('content')]
            if prompt_contents:
                ai_image_prompt = f"Style and details: {' '.join(prompt_contents)}. {ai_image_prompt}"
        
        # Добавляем контекст из системного промпта для изображения ответа ИИ
        if "D&D" in system_context or "Dungeons and Dragons" in system_context:
            ai_image_prompt = f"Dungeons and Dragons themed scene, fantasy RPG style: {ai_image_prompt}"
        
        ai_image_response = client.images.generate(
            model="sdxl-1.0",
            prompt=ai_image_prompt,
            response_format="url"
        )
        ai_image = GeneratedImage(
            url=ai_image_response.data[0].url,
            prompt=ai_image_prompt,
            user_id=current_user.id,
            source='chat'
        )
        db.session.add(ai_image)
        db.session.commit()
        return jsonify({
            "response": ai_response,
            "user_image_url": user_image_response.data[0].url,
            "ai_image_url": ai_image_response.data[0].url,
            "session_id": session.id
        })
    except Exception as e:
        print(f"Chat error: {str(e)}")  # For debugging
        return jsonify({"error": "Failed to generate response. Please try again."}), 500

@app.route('/api/prompts', methods=['GET', 'POST'])
@login_required
def handle_prompts():
    if request.method == 'GET':
        prompts = Prompt.query.filter_by(user_id=current_user.id).all()
        return jsonify([{
            'id': p.id,
            'title': p.title,
            'content': p.content,
            'created_at': p.created_at.isoformat()
        } for p in prompts])
    
    elif request.method == 'POST':
        data = request.get_json()
        prompt = Prompt(
            title=data['title'],
            content=data['content'],
            user_id=current_user.id
        )
        db.session.add(prompt)
        db.session.commit()
        return jsonify({
            'id': prompt.id,
            'title': prompt.title,
            'content': prompt.content
        })

@app.route('/api/prompts/<int:prompt_id>', methods=['PUT', 'DELETE'])
@login_required
def handle_prompt(prompt_id):
    prompt = Prompt.query.filter_by(id=prompt_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'PUT':
        data = request.get_json()
        prompt.title = data['title']
        prompt.content = data['content']
        db.session.commit()
        return jsonify({
            'id': prompt.id,
            'title': prompt.title,
            'content': prompt.content
        })
    
    elif request.method == 'DELETE':
        db.session.delete(prompt)
        db.session.commit()
        return '', 204

@app.route('/api/generate-image', methods=['POST'])
@login_required
def generate_image():
    data = request.get_json()
    prompt = data.get('prompt')
    
    try:
        # Добавляем контекст из системного промпта для лучшей генерации изображений
        system_context = get_system_prompt()
        enhanced_prompt = prompt
        
        # Если системный промпт содержит упоминания D&D, добавляем соответствующий контекст
        if "D&D" in system_context or "Dungeons and Dragons" in system_context:
            enhanced_prompt = f"Dungeons and Dragons themed scene, fantasy RPG style: {prompt}"
        
        client = Client()
        response = client.images.generate(
            model="flux",
            prompt=enhanced_prompt,
            response_format="url"
        )

        # Save generated image to database with enhanced prompt
        image = GeneratedImage(
            url=response.data[0].url,
            prompt=enhanced_prompt,  # Сохраняем улучшенный промпт
            user_id=current_user.id,
            source='image_generator'
        )
        db.session.add(image)
        db.session.commit()
        
        return jsonify({"image_url": response.data[0].url})
        
    except Exception as e:
        print(f"Error generating image: {str(e)}")  # For debugging
        return jsonify({"error": str(e)}), 500

@app.route('/api/images', methods=['GET'])
@login_required
def get_images():
    images = GeneratedImage.query.filter_by(user_id=current_user.id).order_by(GeneratedImage.created_at.desc()).all()
    return jsonify([{
        'id': img.id,
        'url': img.url,
        'prompt': img.prompt,
        'created_at': img.created_at.isoformat(),
        'source': img.source
    } for img in images])

@app.route('/api/images/<int:image_id>', methods=['PUT', 'DELETE'])
@login_required
def handle_image(image_id):
    image = GeneratedImage.query.filter_by(id=image_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'PUT':
        data = request.get_json()
        image.prompt = data['prompt']
        db.session.commit()
        return jsonify({
            'id': image.id,
            'url': image.url,
            'prompt': image.prompt,
            'created_at': image.created_at.isoformat(),
            'source': image.source
        })
    
    elif request.method == 'DELETE':
        db.session.delete(image)
        db.session.commit()
        return '', 204

@app.route('/api/chat-history', methods=['GET'])
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
            'last_message': last_message.content if last_message else None
        })
    return jsonify(result)

@app.route('/api/chat-history/<int:session_id>', methods=['GET'])
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

@app.route('/api/chat-history/<int:session_id>', methods=['DELETE'])
@login_required
def delete_chat_session(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        return '', 404
    db.session.delete(session)
    db.session.commit()
    return '', 204

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)