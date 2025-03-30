from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_bp
from app.core.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import NotificationService

@api_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get user's notifications."""
    user_id = get_jwt_identity()
    limit = request.args.get('limit', default=10, type=int)
    notification_service = NotificationService()
    notifications = notification_service.get_user_notifications(user_id, limit)
    return jsonify([notification.to_dict() for notification in notifications])

@api_bp.route('/notifications/<int:notification_id>', methods=['PUT'])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark a notification as read."""
    user_id = get_jwt_identity()
    notification_service = NotificationService()
    success = notification_service.mark_notification_read(notification_id, user_id)
    
    if success:
        return jsonify({'message': 'Notification marked as read'})
    return jsonify({'error': 'Notification not found'}), 404

@api_bp.route('/notifications/read-all', methods=['PUT'])
@jwt_required()
def mark_all_notifications_read():
    """Mark all notifications as read."""
    user_id = get_jwt_identity()
    try:
        Notification.query.filter_by(
            user_id=user_id,
            status='pending'
        ).update({'status': 'read'})
        db.session.commit()
        return jsonify({'message': 'All notifications marked as read'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/notifications/preferences', methods=['GET'])
@jwt_required()
def get_notification_preferences():
    """Get user's notification preferences."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'email_notifications': user.email_notifications,
        'sms_notifications': user.sms_notifications,
        'in_app_notifications': user.in_app_notifications
    })

@api_bp.route('/notifications/preferences', methods=['PUT'])
@jwt_required()
def update_notification_preferences():
    """Update user's notification preferences."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    try:
        if 'email_notifications' in data:
            user.email_notifications = data['email_notifications']
        if 'sms_notifications' in data:
            user.sms_notifications = data['sms_notifications']
        if 'in_app_notifications' in data:
            user.in_app_notifications = data['in_app_notifications']
        
        user.save()
        return jsonify({'message': 'Notification preferences updated'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/notifications/test', methods=['POST'])
@jwt_required()
def test_notifications():
    """Test notification delivery."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    notification_type = data.get('type', 'in_app')
    notification_service = NotificationService()
    
    try:
        notification = Notification(
            message='This is a test notification',
            type=notification_type,
            user_id=user_id,
            item_id=None  # No specific item for test
        )
        db.session.add(notification)
        db.session.commit()
        
        # Send notification based on type
        if notification_type == 'sms':
            success = notification_service.send_sms_notification(notification)
        elif notification_type == 'email':
            success = notification_service.send_email_notification(notification)
        else:
            success = True  # In-app notifications are already created
        
        if success:
            return jsonify({'message': 'Test notification sent successfully'})
        return jsonify({'error': 'Failed to send test notification'}), 500
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 