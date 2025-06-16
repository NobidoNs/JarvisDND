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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dnd_assistant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Google OAuth2 configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise ValueError("Missing Google OAuth credentials. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file")

client = WebApplicationClient(GOOGLE_CLIENT_ID)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    prompts = db.relationship('Prompt', backref='user', lazy=True)

class Prompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route('/login/callback')
def callback():
    code = request.args.get("code")
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]
    
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
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
            user = User(id=unique_id, name=users_name, email=users_email)
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
    
    print(f"Received message: {message}")  # Debug log
    print(f"Selected prompts: {selected_prompts}")  # Debug log
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        # Generate text response
        client = Client()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful D&D assistant. Provide clear and concise answers about D&D rules, lore, and gameplay."},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        if not response.choices:
            return jsonify({"error": "No response generated"}), 500

        # Create image prompt using the content directly from selected prompts
        image_prompt = message
        if selected_prompts:
            # Extract content from selected prompts
            prompt_contents = [p.get('content', '') for p in selected_prompts if p.get('content')]
            if prompt_contents:
                combined_prompt = f"Dungeons and Dragons scene: {message}. Style and details: {' '.join(prompt_contents)}"
                image_prompt = combined_prompt
                print(f"Using combined prompt: {image_prompt}")  # Debug log

        # Generate image based on the enhanced prompt
        image_response = client.images.generate(
            model="flux",
            prompt=image_prompt,
            response_format="url"
        )
        
        return jsonify({
            "response": response.choices[0].message.content,
            "image_url": image_response.data[0].url
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
        client = Client()
        response = client.images.generate(
            model="flux",
            prompt=prompt,
            response_format="url"
        )
        
        return jsonify({"image_url": response.data[0].url})
        
    except Exception as e:
        print(f"Error generating image: {str(e)}")  # For debugging
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)