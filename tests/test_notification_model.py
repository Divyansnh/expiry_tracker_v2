import pytest
from datetime import datetime
from app.models.notification import Notification
from app.core.extensions import db

def test_notification_creation(app, test_user, test_item):
    """Test notification creation."""
    with app.app_context():
        notification = Notification(
            message='Test notification',
            type='in_app',
            user_id=test_user.id,
            item_id=test_item.id
        )
        notification.save()
        
        assert notification.id is not None
        assert notification.message == 'Test notification'
        assert notification.type == 'in_app'
        assert notification.user_id == test_user.id
        assert notification.item_id == test_item.id
        assert notification.status == 'pending'
        assert notification.priority == 'normal'

def test_notification_update(app, test_notification):
    """Test notification update."""
    with app.app_context():
        test_notification.message = 'Updated notification'
        test_notification.type = 'email'
        test_notification.save()
        
        updated_notification = Notification.query.get(test_notification.id)
        assert updated_notification.message == 'Updated notification'
        assert updated_notification.type == 'email'

def test_notification_deletion(app, test_notification):
    """Test notification deletion."""
    with app.app_context():
        notification_id = test_notification.id
        test_notification.delete()
        
        deleted_notification = Notification.query.get(notification_id)
        assert deleted_notification is None

def test_notification_status(app, test_notification):
    """Test notification status changes."""
    with app.app_context():
        # Mark as sent
        test_notification.mark_sent()
        assert test_notification.status == 'sent'
        assert test_notification.sent_at is not None
        
        # Mark as failed
        test_notification.mark_failed()
        assert test_notification.status == 'failed'

def test_notification_priority(app, test_notification):
    """Test notification priority levels."""
    with app.app_context():
        test_notification.priority = 'high'
        test_notification.save()
        
        updated_notification = Notification.query.get(test_notification.id)
        assert updated_notification.priority == 'high'

def test_notification_to_dict(test_notification):
    """Test notification dictionary conversion."""
    notification_dict = test_notification.to_dict()
    assert notification_dict['id'] == test_notification.id
    assert notification_dict['message'] == test_notification.message
    assert notification_dict['type'] == test_notification.type
    assert notification_dict['user_id'] == test_notification.user_id
    assert notification_dict['item_id'] == test_notification.item_id
    assert notification_dict['status'] == test_notification.status
    assert notification_dict['priority'] == test_notification.priority
    assert 'created_at' in notification_dict
    assert 'updated_at' in notification_dict

def test_notification_relationships(app, test_notification, test_user, test_item):
    """Test notification relationships."""
    with app.app_context():
        assert test_notification.user == test_user
        assert test_notification.item == test_item
        assert test_notification in test_user.notifications
        assert test_notification in test_item.notifications 