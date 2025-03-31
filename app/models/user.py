from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.core.extensions import db
from app.models.base import BaseModel
from datetime import datetime
import jwt
from flask import current_app
from time import time

class User(UserMixin, BaseModel):
    """User model for authentication and user management."""
    
    __tablename__ = 'users'
    
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    password_reset_token = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Notification preferences
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    in_app_notifications = db.Column(db.Boolean, default=True)
    
    # Relationships
    items = db.relationship('Item', backref='user', lazy=True)
    user_notifications = db.relationship('Notification', backref='notification_user', lazy=True)
    
    def set_password(self, password):
        """Set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary."""
        data = super().to_dict()
        data.update({
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'email_notifications': self.email_notifications,
            'sms_notifications': self.sms_notifications,
            'in_app_notifications': self.in_app_notifications
        })
        return data
    
    def __repr__(self):
        """String representation of the user."""
        return f'<User {self.username}>'

    def get_password_reset_token(self, expires_in=3600):
        """Generate a password reset token."""
        return jwt.encode(
            {
                'reset_password': self.id,
                'email': self.email,
                'exp': time() + expires_in,
                'used': False
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    def invalidate_reset_token(self):
        """Invalidate any existing password reset tokens."""
        self.password_reset_token = None
        db.session.commit()

    @staticmethod
    def verify_password_reset_token(token, invalidate=True):
        """Verify password reset token and optionally mark it as used."""
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'],
                               algorithms=['HS256'])
            id = payload['reset_password']
            email = payload.get('email')
            used = payload.get('used', False)
            exp = payload.get('exp')
            
            current_app.logger.info(f"Verifying password reset token for user {id}")
            current_app.logger.debug(f"Token payload: {payload}")
            
            # Check if token has expired
            if exp and time() > exp:
                current_app.logger.warning(f"Token has expired for user {id}")
                return None
                
            # Check if token has already been used
            if used:
                current_app.logger.warning(f"Token has already been used for user {id}")
                return None
                
            user = User.query.get(id)
            if not user:
                current_app.logger.warning(f"User {id} not found")
                return None
                
            # Verify that the email matches
            if user.email != email:
                current_app.logger.warning(f"Email mismatch for user {id}. Token email: {email}, User email: {user.email}")
                return None
                
            # Verify that the token matches what's stored in the database
            if user.password_reset_token != token:
                current_app.logger.warning(f"Token mismatch for user {id}")
                return None
                
            # Invalidate the token if requested
            if invalidate:
                user.password_reset_token = None
                db.session.commit()
                current_app.logger.info(f"Token invalidated for user {id}")
                
            return user
        except jwt.ExpiredSignatureError:
            current_app.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            current_app.logger.warning(f"Invalid token: {str(e)}")
            return None
        except Exception as e:
            current_app.logger.error(f"Error verifying token: {str(e)}")
            return None 