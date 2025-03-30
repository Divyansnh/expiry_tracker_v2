import pytest
from datetime import datetime, timedelta
from app.models.item import Item
from app.core.extensions import db

def test_item_creation(app, test_user):
    """Test item creation."""
    with app.app_context():
        item = Item(
            name='Test Item',
            description='Test Description',
            quantity=10,
            unit='pieces',
            user_id=test_user.id
        )
        item.save()
        
        assert item.id is not None
        assert item.name == 'Test Item'
        assert item.description == 'Test Description'
        assert item.quantity == 10
        assert item.unit == 'pieces'
        assert item.user_id == test_user.id

def test_item_update(app, test_item):
    """Test item update."""
    with app.app_context():
        test_item.name = 'Updated Item'
        test_item.quantity = 20
        test_item.save()
        
        updated_item = Item.query.get(test_item.id)
        assert updated_item.name == 'Updated Item'
        assert updated_item.quantity == 20

def test_item_deletion(app, test_item):
    """Test item deletion."""
    with app.app_context():
        item_id = test_item.id
        test_item.delete()
        
        deleted_item = Item.query.get(item_id)
        assert deleted_item is None

def test_item_expiry_dates(app, test_item):
    """Test item expiry date calculations."""
    with app.app_context():
        # Set expiry date to tomorrow
        test_item.expiry_date = datetime.now().date() + timedelta(days=1)
        test_item.save()
        
        assert test_item.days_until_expiry == 1
        assert not test_item.is_expired
        assert test_item.is_near_expiry

        # Set expiry date to yesterday
        test_item.expiry_date = datetime.now().date() - timedelta(days=1)
        test_item.save()
        
        assert test_item.days_until_expiry < 0
        assert test_item.is_expired
        assert not test_item.is_near_expiry

def test_item_discount(app, test_item):
    """Test item discount calculations."""
    with app.app_context():
        test_item.purchase_price = 100
        test_item.selling_price = 120
        test_item.set_discount(20)  # 20% discount
        
        assert test_item.discounted_price == 96  # 120 - 20%

def test_item_to_dict(test_item):
    """Test item dictionary conversion."""
    item_dict = test_item.to_dict()
    assert item_dict['id'] == test_item.id
    assert item_dict['name'] == test_item.name
    assert item_dict['description'] == test_item.description
    assert item_dict['quantity'] == test_item.quantity
    assert item_dict['unit'] == test_item.unit
    assert item_dict['user_id'] == test_item.user_id
    assert 'created_at' in item_dict
    assert 'updated_at' in item_dict

def test_item_relationships(app, test_item, test_user):
    """Test item relationships."""
    with app.app_context():
        assert test_item.user == test_user
        assert test_item in test_user.items 