from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.image_service import ImageService
from models import GeneratedImage

images_bp = Blueprint('images', __name__, url_prefix='/api')
image_service = ImageService()

@images_bp.route('/generate-image', methods=['POST'])
@login_required
def generate_image():
    data = request.get_json()
    prompt = data.get('prompt')
    
    try:
        result = image_service.generate_image(current_user.id, prompt)
        return jsonify(result)
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return jsonify({"error": str(e)}), 500

@images_bp.route('/images', methods=['GET'])
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

@images_bp.route('/images/<int:image_id>', methods=['PUT'])
@login_required
def update_image(image_id):
    from models import db
    image = GeneratedImage.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not image:
        return '', 404
    
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

@images_bp.route('/images/<int:image_id>', methods=['DELETE'])
@login_required
def delete_image(image_id):
    from models import db
    image = GeneratedImage.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not image:
        return '', 404
    
    db.session.delete(image)
    db.session.commit()
    return '', 204 