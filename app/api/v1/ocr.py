from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from app.api.v1 import api_bp
from app.core.extensions import db
from app.core.config import Config
from app.services.ocr_service import OCRService
from app.models.item import Item

ocr_service = OCRService()

@api_bp.route('/ocr/extract', methods=['POST'])
@jwt_required()
def extract_expiry_date():
    """Extract expiry date from an image."""
    user_id = get_jwt_identity()
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file or not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Process the image
        result = ocr_service.process_image(filepath)
        
        # Clean up the uploaded file
        os.remove(filepath)
        
        if result and result.get('expiry_date'):
            return jsonify(result)
        return jsonify({'error': 'No expiry date found in image'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/ocr/validate', methods=['POST'])
@jwt_required()
def validate_expiry_date():
    """Validate an extracted expiry date."""
    data = request.get_json()
    
    if not data or 'expiry_date' not in data:
        return jsonify({'error': 'No expiry date provided'}), 400
    
    try:
        is_valid = ocr_service.validate_date(data['expiry_date'])
        return jsonify({
            'is_valid': is_valid,
            'message': 'Valid expiry date' if is_valid else 'Invalid expiry date'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/ocr/items/<int:item_id>/update', methods=['POST'])
@jwt_required()
def update_item_expiry_from_image(item_id):
    """Update item expiry date from image."""
    user_id = get_jwt_identity()
    item = Item.query.filter_by(id=item_id, user_id=user_id).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file or not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Process the image
        result = ocr_service.process_image(filepath)
        
        # Clean up the uploaded file
        os.remove(filepath)
        
        if result and result.get('expiry_date'):
            item.expiry_date = result['expiry_date']
            item.save()
            return jsonify({
                'message': 'Item expiry date updated successfully',
                'item': item.to_dict()
            })
        return jsonify({'error': 'No expiry date found in image'}), 404
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/ocr/batch', methods=['POST'])
@jwt_required()
def batch_process_images():
    """Process multiple images in batch."""
    user_id = get_jwt_identity()
    
    if 'images' not in request.files:
        return jsonify({'error': 'No images provided'}), 400
    
    files = request.files.getlist('images')
    if not files:
        return jsonify({'error': 'No selected files'}), 400
    
    results = []
    for file in files:
        if file.filename == '':
            continue
            
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            results.append({
                'filename': file.filename,
                'error': 'Invalid file type'
            })
            continue
        
        try:
            # Save the uploaded file
            filename = secure_filename(file.filename)
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Process the image
            result = ocr_service.process_image(filepath)
            
            # Clean up the uploaded file
            os.remove(filepath)
            
            results.append({
                'filename': file.filename,
                'result': result
            })
            
        except Exception as e:
            results.append({
                'filename': file.filename,
                'error': str(e)
            })
    
    return jsonify({
        'total_files': len(files),
        'results': results
    }) 