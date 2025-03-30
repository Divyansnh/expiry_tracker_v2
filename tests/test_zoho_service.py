import pytest
from unittest.mock import patch, MagicMock
from app.services.zoho_service import ZohoService
from app.models.user import User

@pytest.fixture
def zoho_service():
    """Create a Zoho service instance."""
    return ZohoService()

def test_get_auth_url(zoho_service):
    """Test getting Zoho authentication URL."""
    auth_url = zoho_service.get_auth_url()
    assert auth_url.startswith('https://accounts.zoho.com/oauth/v2/auth')
    assert 'client_id=' in auth_url
    assert 'redirect_uri=' in auth_url
    assert 'response_type=code' in auth_url
    assert 'scope=' in auth_url

@patch('app.services.zoho_service.requests.post')
def test_handle_callback_success(mock_post, zoho_service):
    """Test successful Zoho callback handling."""
    # Mock the token response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'access_token': 'test_access_token',
        'refresh_token': 'test_refresh_token',
        'expires_in': 3600
    }
    mock_post.return_value = mock_response
    
    # Test callback handling
    success = zoho_service.handle_callback('test_code')
    assert success is True
    mock_post.assert_called_once()

@patch('app.services.zoho_service.requests.post')
def test_handle_callback_failure(mock_post, zoho_service):
    """Test failed Zoho callback handling."""
    # Mock the error response
    mock_response = MagicMock()
    mock_response.json.return_value = {'error': 'invalid_code'}
    mock_post.return_value = mock_response
    
    # Test callback handling
    success = zoho_service.handle_callback('invalid_code')
    assert success is False

@patch('app.services.zoho_service.requests.post')
def test_refresh_token_success(mock_post, zoho_service):
    """Test successful token refresh."""
    # Mock the token response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'access_token': 'new_access_token',
        'expires_in': 3600
    }
    mock_post.return_value = mock_response
    
    # Test token refresh
    success = zoho_service.refresh_token('test_refresh_token')
    assert success is True
    mock_post.assert_called_once()

@patch('app.services.zoho_service.requests.post')
def test_refresh_token_failure(mock_post, zoho_service):
    """Test failed token refresh."""
    # Mock the error response
    mock_response = MagicMock()
    mock_response.json.return_value = {'error': 'invalid_token'}
    mock_post.return_value = mock_response
    
    # Test token refresh
    success = zoho_service.refresh_token('invalid_token')
    assert success is False

@patch('app.services.zoho_service.requests.get')
def test_get_inventory_data_success(mock_get, zoho_service):
    """Test successful inventory data retrieval."""
    # Mock the inventory response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'items': [
            {
                'id': 1,
                'name': 'Test Item',
                'quantity': 10,
                'unit': 'pieces'
            }
        ]
    }
    mock_get.return_value = mock_response
    
    # Test inventory data retrieval
    data = zoho_service.get_inventory_data('test_access_token')
    assert data is not None
    assert 'items' in data
    assert len(data['items']) == 1
    mock_get.assert_called_once()

@patch('app.services.zoho_service.requests.get')
def test_get_inventory_data_failure(mock_get, zoho_service):
    """Test failed inventory data retrieval."""
    # Mock the error response
    mock_response = MagicMock()
    mock_response.json.return_value = {'error': 'invalid_token'}
    mock_get.return_value = mock_response
    
    # Test inventory data retrieval
    data = zoho_service.get_inventory_data('invalid_token')
    assert data is None

@patch('app.services.zoho_service.ZohoService.get_inventory_data')
def test_sync_inventory_success(mock_get_data, zoho_service, app, test_user):
    """Test successful inventory synchronization."""
    # Mock the inventory data
    mock_get_data.return_value = {
        'items': [
            {
                'id': 1,
                'name': 'Test Item',
                'quantity': 10,
                'unit': 'pieces'
            }
        ]
    }
    
    # Test inventory sync
    success = zoho_service.sync_inventory(test_user)
    assert success is True
    mock_get_data.assert_called_once()

@patch('app.services.zoho_service.ZohoService.get_inventory_data')
def test_sync_inventory_failure(mock_get_data, zoho_service, app, test_user):
    """Test failed inventory synchronization."""
    # Mock the error response
    mock_get_data.return_value = None
    
    # Test inventory sync
    success = zoho_service.sync_inventory(test_user)
    assert success is False

def test_logout(zoho_service):
    """Test logout functionality."""
    zoho_service.logout()
    # Add assertions based on your logout implementation 