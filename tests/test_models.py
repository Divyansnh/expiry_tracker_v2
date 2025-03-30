import pytest
from app.models.user import User
from app.core.extensions import db

def test_password_hashing(test_user):
    """Test password hashing."""
    assert test_user.check_password('password123')
    assert not test_user.check_password('wrongpassword')

def test_user_creation(app):
    """Test user creation."""
    with app.app_context():
        user = User(username='newuser', email='new@example.com')
        user.set_password('password123')
        user.save()
        
        assert user.id is not None
        assert user.username == 'newuser'
        assert user.email == 'new@example.com'
        assert user.is_active is True
        assert user.is_admin is False

def test_user_update(app, test_user):
    """Test user update."""
    with app.app_context():
        test_user.username = 'updateduser'
        test_user.email = 'updated@example.com'
        test_user.save()
        
        updated_user = User.query.get(test_user.id)
        assert updated_user.username == 'updateduser'
        assert updated_user.email == 'updated@example.com'

def test_user_deletion(app, test_user):
    """Test user deletion."""
    with app.app_context():
        user_id = test_user.id
        test_user.delete()
        
        deleted_user = User.query.get(user_id)
        assert deleted_user is None

def test_user_notification_preferences(app, test_user):
    """Test user notification preferences."""
    with app.app_context():
        test_user.email_notifications = False
        test_user.sms_notifications = True
        test_user.in_app_notifications = False
        test_user.save()
        
        updated_user = User.query.get(test_user.id)
        assert updated_user.email_notifications is False
        assert updated_user.sms_notifications is True
        assert updated_user.in_app_notifications is False

def test_user_to_dict(test_user):
    """Test user dictionary conversion."""
    user_dict = test_user.to_dict()
    assert user_dict['id'] == test_user.id
    assert user_dict['username'] == test_user.username
    assert user_dict['email'] == test_user.email
    assert user_dict['is_active'] == test_user.is_active
    assert user_dict['is_admin'] == test_user.is_admin
    assert 'password_hash' not in user_dict 