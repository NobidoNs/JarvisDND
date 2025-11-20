from flask import Flask

from config import Config
from routes.chat import chat_bp
from routes.images import images_bp
from routes.main import main_bp
from routes.prompts import prompts_bp


def create_app():
    """Application factory pattern without external dependencies."""

    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(prompts_bp)
    app.register_blueprint(images_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)