import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///expiry_tracker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Zoho API Configuration
    ZOHO_CLIENT_ID = os.environ.get('ZOHO_CLIENT_ID')
    ZOHO_CLIENT_SECRET = os.environ.get('ZOHO_CLIENT_SECRET')
    ZOHO_REDIRECT_URI = os.environ.get('ZOHO_REDIRECT_URI') or 'http://localhost:5000/callback'
    ZOHO_ORGANIZATION_ID = os.environ.get('ZOHO_ORGANIZATION_ID')
    
    # APScheduler Configuration
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "UTC" 