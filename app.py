from flask import Flask
from flask_login import LoginManager
from models import db, User
from config import Config
from routes.main import main_bp
from routes.chat import chat_bp
from routes.prompts import prompts_bp
from routes.images import images_bp

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = Config.SQLALCHEMY_TRACK_MODIFICATIONS
    
    # Validate configuration
    Config.validate_config()
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, user_id)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(prompts_bp)
    app.register_blueprint(images_bp)
    
    # Initialize database
    with app.app_context():
        db.create_all()
        print("Database tables created successfully")
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) 