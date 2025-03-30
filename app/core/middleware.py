from functools import wraps
from flask import request, g, current_app, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User
import time

def log_request(app):
    """Log request details."""
    start_time = time.time()
    
    @app.after_request
    def after_request(response):
        if not app.debug:
            return response
            
        duration = time.time() - start_time
        app.logger.info(
            f'Request: {request.method} {request.url} - '
            f'Status: {response.status_code} - '
            f'Duration: {duration:.2f}s'
        )
        return response

def require_auth(f):
    """Require authentication for routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        g.user = User.query.get(user_id)
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    """Require admin privileges for routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        
        g.user = user
        return f(*args, **kwargs)
    return decorated

def handle_cors(app):
    """Handle CORS headers."""
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

def rate_limit():
    """Rate limiting middleware."""
    # TODO: Implement rate limiting
    pass

def validate_request(app):
    """Validate request data."""
    @app.before_request
    def before_request():
        if request.is_json:
            try:
                request.get_json()
            except Exception as e:
                app.logger.error(f'Invalid JSON in request: {str(e)}')
                return jsonify({'error': 'Invalid JSON'}), 400 