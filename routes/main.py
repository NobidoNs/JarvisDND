from flask import Blueprint, jsonify, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@main_bp.route("/api/available-models", methods=["GET"])
def available_models():
    return jsonify(
        {
            "text_models": {
                "gpt-4": "GPT-4",
                "gpt-4o": "GPT-4o",
                "gpt-3.5-turbo": "GPT-3.5 Turbo",
            },
            "image_models": {
                "sdxl-1.0": "Stable Diffusion XL 1.0",
                "flux": "Flux",
            },
        }
    )