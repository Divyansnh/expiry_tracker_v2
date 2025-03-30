from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.core.extensions import db
from app.models.base import BaseModel
from datetime import datetime

class User(UserMixin, BaseModel):
    """User model for authentication and user management."""
    
    __tablename__ = 'users'
    
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
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