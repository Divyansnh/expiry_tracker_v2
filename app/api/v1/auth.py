from flask import jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.api.v1 import api_bp
from app.core.extensions import db
from app.models.user import User
from app.services.zoho_service import ZohoService

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    try:
        user = User(
            username=data['username'],
            email=data['email']
        )
        user.set_password(data['password'])
        user.save()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token."""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@api_bp.route('/auth/zoho/login', methods=['GET'])
@jwt_required()
def zoho_login():
    """Initiate Zoho OAuth login."""
    try:
        zoho_service = ZohoService()
        auth_url = zoho_service.get_auth_url()
        return jsonify({'auth_url': auth_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/auth/zoho/callback', methods=['GET'])
@jwt_required()
def zoho_callback():
    """Handle Zoho OAuth callback."""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'No code provided'}), 400
        
        zoho_service = ZohoService()
        success = zoho_service.handle_callback(code)
        if success:
            return jsonify({'message': 'Successfully connected to Zoho'})
        return jsonify({'error': 'Failed to connect to Zoho'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/auth/zoho/logout', methods=['POST'])
@jwt_required()
def zoho_logout():
    """Logout from Zoho."""
    try:
        zoho_service = ZohoService()
        zoho_service.logout()
        return jsonify({'message': 'Successfully disconnected from Zoho'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()) 