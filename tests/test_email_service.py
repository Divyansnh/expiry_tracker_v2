import pytest
from app.services.email_service import EmailService
from app.models.user import User
from app.models.item import Item
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

@pytest.fixture
def test_user():
    return User(
        username='testuser',
        email='test@example.com'
    )

@pytest.fixture
def test_items(test_user):
    today = datetime.utcnow()
    return [
        Item(
            name='Test Item 1',
            expiry_date=today + timedelta(days=2),
            user_id=test_user.id
        ),
        Item(
            name='Test Item 2',
            expiry_date=today + timedelta(days=5),
            user_id=test_user.id
        ),
        Item(
            name='Test Item 3',
            expiry_date=today + timedelta(days=10),
            user_id=test_user.id
        )
    ]

def test_send_daily_notification_email(test_user, test_items):
    with patch('app.services.email_service.EmailService.send_email') as mock_send_email:
        # Configure mock to return success
        mock_send_email.return_value = True
        
        # Test with items needing attention
        notification_items = [
            {'name': 'Test Item 1', 'days_until_expiry': 2, 'priority': 'high'},
            {'name': 'Test Item 2', 'days_until_expiry': 5, 'priority': 'normal'}
        ]
        
        success = EmailService.send_daily_notification_email(test_user, notification_items)
        
        assert success is True
        mock_send_email.assert_called_once()
        
        # Verify email content
        call_args = mock_send_email.call_args[1]
        assert call_args['recipient'] == test_user.email
        assert 'Test Item 1' in call_args['html_content']
        assert 'Test Item 2' in call_args['html_content']

def test_send_password_reset_email(test_user):
    with patch('app.services.email_service.EmailService.send_email') as mock_send_email:
        # Configure mock to return success
        mock_send_email.return_value = True
        
        # Test password reset email
        reset_url = 'http://localhost:5000/auth/reset-password/token123'
        success = EmailService.send_password_reset_email(test_user.email, reset_url)
        
        assert success is True
        mock_send_email.assert_called_once()
        
        # Verify email content
        call_args = mock_send_email.call_args[1]
        assert call_args['recipient'] == test_user.email
        assert 'password reset' in call_args['subject'].lower()
        assert reset_url in call_args['html_content']

def test_send_email_failure():
    with patch('app.services.email_service.smtplib.SMTP') as mock_smtp:
        # Configure mock to raise an exception
        mock_smtp.side_effect = Exception('SMTP Error')
        
        success = EmailService.send_email(
            recipient='test@example.com',
            subject='Test Subject',
            html_content='Test Content'
        )
        
        assert success is False 