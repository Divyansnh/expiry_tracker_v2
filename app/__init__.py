import logging
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from app.core.config import Config
from app.core.extensions import db, login_manager, jwt, migrate, cors, init_extensions, scheduler, mail
from app.core.errors import register_error_handlers
from app.core.middleware import log_request, handle_cors, validate_request
from app.routes import main_bp, auth_bp
from app.api.v1 import api_bp
from app.tasks.cleanup import cleanup_expired_items

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config_class)
    
    # Initialize extensions
    init_extensions(app)
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    scheduler.init_app(app)
    mail.init_app(app)
    
    # Schedule cleanup task to run daily at midnight
    scheduler.add_job(
        id='cleanup_expired_items',
        func=cleanup_expired_items,
        trigger='cron',
        hour=0,
        minute=0
    )
    
    # Start the scheduler
    scheduler.start()
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register middleware
    log_request(app)
    handle_cors(app)
    validate_request(app)
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app 