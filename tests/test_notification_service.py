import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.services.notification_service import NotificationService
from app.models.item import Item
from app.models.notification import Notification

@pytest.fixture
def notification_service():
    """Create a notification service instance."""
    return NotificationService()

def test_check_expiry_dates(app, test_item, notification_service):
    """Test checking expiry dates."""
    with app.app_context():
        # Set expiry date to tomorrow
        test_item.expiry_date = datetime.now().date() + timedelta(days=1)
        test_item.save()
        
        # Check expiry dates
        notification_service.check_expiry_dates()
        
        # Verify notification was created
        notification = Notification.query.filter_by(
            item_id=test_item.id,
            type='in_app'
        ).first()
        
        assert notification is not None
        assert notification.priority == 'critical'
        assert notification.status == 'pending'

def test_create_notification(app, test_item, notification_service):
    """Test notification creation."""
    with app.app_context():
        # Create notification
        notification = notification_service._create_notification(
            test_item,
            'Test message',
            'warning'
        )
        
        assert notification is not None
        assert notification.message == 'Test message'
        assert notification.type == 'in_app'
        assert notification.priority == 'warning'
        assert notification.status == 'pending'
        assert notification.user_id == test_item.user_id
        assert notification.item_id == test_item.id

def test_duplicate_notification_prevention(app, test_item, notification_service):
    """Test prevention of duplicate notifications."""
    with app.app_context():
        # Create first notification
        notification_service._create_notification(
            test_item,
            'Test message',
            'warning'
        )
        
        # Try to create duplicate notification
        notification = notification_service._create_notification(
            test_item,
            'Test message',
            'warning'
        )
        
        assert notification is None

@patch('app.services.notification_service.twilio_client')
def test_send_sms_notification_success(mock_twilio, notification_service, test_notification):
    """Test successful SMS notification sending."""
    # Mock Twilio client
    mock_message = MagicMock()
    mock_message.sid = 'test_sid'
    mock_twilio.messages.create.return_value = mock_message
    
    # Send notification
    success = notification_service.send_sms_notification(test_notification)
    
    assert success is True
    assert test_notification.status == 'sent'
    assert test_notification.sent_at is not None
    mock_twilio.messages.create.assert_called_once()

@patch('app.services.notification_service.twilio_client')
def test_send_sms_notification_failure(mock_twilio, notification_service, test_notification):
    """Test failed SMS notification sending."""
    # Mock Twilio client error
    mock_twilio.messages.create.side_effect = Exception('Twilio error')
    
    # Send notification
    success = notification_service.send_sms_notification(test_notification)
    
    assert success is False
    assert test_notification.status == 'failed'

@patch('app.services.notification_service.mail')
def test_send_email_notification_success(mock_mail, notification_service, test_notification):
    """Test successful email notification sending."""
    # Mock mail send
    mock_mail.send.return_value = True
    
    # Send notification
    success = notification_service.send_email_notification(test_notification)
    
    assert success is True
    assert test_notification.status == 'sent'
    assert test_notification.sent_at is not None
    mock_mail.send.assert_called_once()

@patch('app.services.notification_service.mail')
def test_send_email_notification_failure(mock_mail, notification_service, test_notification):
    """Test failed email notification sending."""
    # Mock mail send error
    mock_mail.send.side_effect = Exception('Mail error')
    
    # Send notification
    success = notification_service.send_email_notification(test_notification)
    
    assert success is False
    assert test_notification.status == 'failed'

def test_get_user_notifications(app, test_user, notification_service):
    """Test retrieving user notifications."""
    with app.app_context():
        # Create multiple notifications
        for i in range(5):
            notification = Notification(
                message=f'Test notification {i}',
                type='in_app',
                user_id=test_user.id
            )
            notification.save()
        
        # Get notifications
        notifications = notification_service.get_user_notifications(test_user.id, limit=3)
        
        assert len(notifications) == 3
        assert all(n.user_id == test_user.id for n in notifications)

def test_mark_notification_read(app, test_notification, notification_service):
    """Test marking notification as read."""
    with app.app_context():
        success = notification_service.mark_notification_read(
            test_notification.id,
            test_notification.user_id
        )
        
        assert success is True
        assert test_notification.status == 'read'

def test_mark_notification_read_invalid(app, notification_service):
    """Test marking invalid notification as read."""
    with app.app_context():
        success = notification_service.mark_notification_read(999, 999)
        assert success is False 