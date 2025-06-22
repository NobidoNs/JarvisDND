from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import Prompt

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    from auth import get_google_auth_url
    return redirect(get_google_auth_url())

@main_bp.route('/login/callback')
def callback():
    from auth import handle_google_callback
    success, user = handle_google_callback()
    
    if success:
        return redirect(url_for('main.dashboard'))
    return "User email not verified by Google.", 400

@main_bp.route('/dashboard')
@login_required
def dashboard():
    prompts = Prompt.query.filter_by(user_id=current_user.id).order_by(Prompt.created_at.desc()).all()
    return render_template('dashboard.html', prompts=prompts)

@main_bp.route('/logout')
@login_required
def logout():
    from flask_login import logout_user
    logout_user()
    return redirect(url_for('main.index')) 