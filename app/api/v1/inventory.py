from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_bp
from app.core.extensions import db
from app.models.item import Item
from app.models.user import User
from app.services.zoho_service import ZohoService
from app.services.notification_service import NotificationService

@api_bp.route('/inventory', methods=['GET'])
@jwt_required()
def get_inventory():
    """Get user's inventory items."""
    user_id = get_jwt_identity()
    items = Item.query.filter_by(user_id=user_id).all()
    return jsonify([item.to_dict() for item in items])

@api_bp.route('/inventory/sync', methods=['POST'])
@jwt_required()
def sync_inventory():
    """Sync inventory with Zoho."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    zoho_service = ZohoService()
    success = zoho_service.sync_inventory(user)
    if success:
        return jsonify({'message': 'Inventory synced successfully'})
    return jsonify({'error': 'Failed to sync inventory'}), 500

@api_bp.route('/inventory/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    """Get a specific inventory item."""
    user_id = get_jwt_identity()
    item = Item.query.filter_by(id=item_id, user_id=user_id).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    return jsonify(item.to_dict())

@api_bp.route('/inventory/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    """Update an inventory item."""
    user_id = get_jwt_identity()
    item = Item.query.filter_by(id=item_id, user_id=user_id).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    data = request.get_json()
    
    try:
        # Update fields if provided
        for field in ['name', 'quantity', 'unit', 'expiry_date', 'location', 'notes']:
            if field in data:
                setattr(item, field, data[field])
        
        # Handle expiry date
        if 'expiry_date' in data:
            item.expiry_date = data['expiry_date']
        
        # Handle discount
        if 'discount_percentage' in data:
            item.set_discount(data['discount_percentage'])
        
        item.save()
        
        # Check for notifications
        notification_service = NotificationService()
        notification_service.check_expiry_dates()
        
        return jsonify(item.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/inventory/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    """Delete an inventory item."""
    user_id = get_jwt_identity()
    item = Item.query.filter_by(id=item_id, user_id=user_id).first()
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    try:
        item.delete()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/inventory/expiring', methods=['GET'])
@jwt_required()
def get_expiring_items():
    """Get items that are expiring soon."""
    user_id = get_jwt_identity()
    items = Item.query.filter_by(user_id=user_id).all()
    expiring_items = [item for item in items if item.is_near_expiry]
    return jsonify([item.to_dict() for item in expiring_items])

@api_bp.route('/inventory/expired', methods=['GET'])
@jwt_required()
def get_expired_items():
    """Get expired items."""
    user_id = get_jwt_identity()
    items = Item.query.filter_by(user_id=user_id).all()
    expired_items = [item for item in items if item.is_expired]
    return jsonify([item.to_dict() for item in expired_items]) 