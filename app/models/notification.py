from datetime import datetime
from app.core.extensions import db

class Notification(db.Model):
    """Model for storing user notifications."""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'))
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(20), default='in_app')
    priority = db.Column(db.String(20), default='normal')
    status = db.Column(db.String(20), default='pending')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert notification to dictionary."""
        return {
            'id': self.id,
            'message': self.message,
            'type': self.type,
            'priority': self.priority,
            'status': self.status,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.message}>' 