import pytest
from datetime import datetime, timedelta
from app.models.user import User
from app.models.item import Item
from app.models.notification import Notification

def test_register(client):
    """Test user registration."""
    response = client.post('/api/v1/auth/register', json={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123'
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'User registered successfully'
    assert 'user' in data
    assert data['user']['username'] == 'newuser'
    assert data['user']['email'] == 'new@example.com'

def test_register_existing_username(client, test_user):
    """Test registration with existing username."""
    response = client.post('/api/v1/auth/register', json={
        'username': test_user.username,
        'email': 'another@example.com',
        'password': 'password123'
    })
    
    assert response.status_code == 409
    data = response.get_json()
    assert data['error'] == 'Username already exists'

def test_login(client, test_user):
    """Test user login."""
    response = client.post('/api/v1/auth/login', json={
        'username': test_user.username,
        'password': 'password123'
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    assert 'user' in data
    assert data['user']['username'] == test_user.username

def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post('/api/v1/auth/login', json={
        'username': 'wronguser',
        'password': 'wrongpass'
    })
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == 'Invalid credentials'

def test_get_inventory(client, test_user, auth_headers):
    """Test getting user's inventory."""
    response = client.get('/api/v1/inventory', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_get_inventory_unauthorized(client):
    """Test getting inventory without authentication."""
    response = client.get('/api/v1/inventory')
    
    assert response.status_code == 401

def test_get_item(client, test_item, auth_headers):
    """Test getting a specific item."""
    response = client.get(f'/api/v1/inventory/{test_item.id}', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == test_item.id

def test_get_item_not_found(client, auth_headers):
    """Test getting non-existent item."""
    response = client.get('/api/v1/inventory/999', headers=auth_headers)
    
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Item not found'

def test_update_item(client, test_item, auth_headers):
    """Test updating an item."""
    response = client.put(f'/api/v1/inventory/{test_item.id}', headers=auth_headers, json={
        'name': 'Updated Item',
        'quantity': 20
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Updated Item'
    assert data['quantity'] == 20

def test_delete_item(client, test_item, auth_headers):
    """Test deleting an item."""
    response = client.delete(f'/api/v1/inventory/{test_item.id}', headers=auth_headers)
    
    assert response.status_code == 204
    
    # Verify item is deleted
    response = client.get(f'/api/v1/inventory/{test_item.id}', headers=auth_headers)
    assert response.status_code == 404

def test_get_expiring_items(client, test_item, auth_headers):
    """Test getting expiring items."""
    # Set expiry date to tomorrow
    test_item.expiry_date = datetime.now().date() + timedelta(days=1)
    test_item.save()
    
    response = client.get('/api/v1/inventory/expiring', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]['id'] == test_item.id

def test_get_expired_items(client, test_item, auth_headers):
    """Test getting expired items."""
    # Set expiry date to yesterday
    test_item.expiry_date = datetime.now().date() - timedelta(days=1)
    test_item.save()
    
    response = client.get('/api/v1/inventory/expired', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]['id'] == test_item.id

def test_get_notifications(client, test_notification, auth_headers):
    """Test getting user's notifications."""
    response = client.get('/api/v1/notifications', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]['id'] == test_notification.id

def test_mark_notification_read(client, test_notification, auth_headers):
    """Test marking notification as read."""
    response = client.put(f'/api/v1/notifications/{test_notification.id}', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Notification marked as read'

def test_mark_all_notifications_read(client, test_notification, auth_headers):
    """Test marking all notifications as read."""
    response = client.put('/api/v1/notifications/read-all', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'All notifications marked as read'

def test_get_notification_preferences(client, test_user, auth_headers):
    """Test getting notification preferences."""
    response = client.get('/api/v1/notifications/preferences', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'email_notifications' in data
    assert 'sms_notifications' in data
    assert 'in_app_notifications' in data

def test_update_notification_preferences(client, test_user, auth_headers):
    """Test updating notification preferences."""
    response = client.put('/api/v1/notifications/preferences', headers=auth_headers, json={
        'email_notifications': False,
        'sms_notifications': True,
        'in_app_notifications': False
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Notification preferences updated' 