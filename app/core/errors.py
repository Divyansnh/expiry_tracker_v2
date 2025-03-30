from flask import jsonify, render_template, request

def register_error_handlers(app):
    """Register error handlers for the application."""
    
    def is_api_request():
        return request.path.startswith('/api/')
    
    @app.errorhandler(400)
    def bad_request_error(error):
        if is_api_request():
            return jsonify({'error': 'Bad Request', 'message': str(error)}), 400
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        if is_api_request():
            return jsonify({'error': 'Unauthorized', 'message': str(error)}), 401
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        if is_api_request():
            return jsonify({'error': 'Forbidden', 'message': str(error)}), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        if is_api_request():
            return jsonify({'error': 'Not Found', 'message': str(error)}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if is_api_request():
            return jsonify({'error': 'Internal Server Error', 'message': str(error)}), 500
        return render_template('errors/500.html'), 500 