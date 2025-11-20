from flask import Blueprint, jsonify, request

from services.image_service import ImageService
from utils.local_user import get_user_id

images_bp = Blueprint("images", __name__, url_prefix="/api")
image_service = ImageService()


@images_bp.route("/generate-image", methods=["POST"])
def generate_image():
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required to generate images."}), 400
    try:
        result = image_service.generate_image(get_user_id(), prompt)
        return jsonify(result)
    except Exception as exc:
        print(f"Error generating image: {exc}")
        return jsonify({"error": "Failed to generate image."}), 500


@images_bp.route("/images", methods=["GET"])
def get_images():
    images = image_service.list_images(get_user_id())
    return jsonify(images)


@images_bp.route("/images/<int:image_id>", methods=["PUT"])
def update_image(image_id):
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400
    image = image_service.update_image(image_id, get_user_id(), prompt)
    if image:
        return jsonify(image)
    return "", 404


@images_bp.route("/images/<int:image_id>", methods=["DELETE"])
def delete_image(image_id):
    if image_service.delete_image(image_id, get_user_id()):
        return "", 204
    return "", 404