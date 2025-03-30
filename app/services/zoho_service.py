import os
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app, session, request
from app.core.extensions import db
from app.models.item import Item
from app.models.user import User

class ZohoService:
    """Service for handling Zoho API interactions."""
    
    def __init__(self):
        self.client_id = current_app.config['ZOHO_CLIENT_ID']
        self.client_secret = current_app.config['ZOHO_CLIENT_SECRET']
        self.redirect_uri = current_app.config['ZOHO_REDIRECT_URI']
        self.base_url = "https://www.zohoapis.eu/inventory/v1"
    
    def get_access_token(self) -> Optional[str]:
        """Get the current access token from session."""
        token = session.get('zoho_access_token')
        expires_at = session.get('zoho_token_expires_at')
        
        # Check if token exists and is not expired
        if token and expires_at:
            if int(time.time()) >= expires_at:
                current_app.logger.info("Access token expired, attempting to refresh")
                if self.refresh_token():
                    return session.get('zoho_access_token')
                return None
            return token
            
        current_app.logger.error("No access token available")
        return None
    
    def get_refresh_token(self) -> Optional[str]:
        """Get the refresh token from session."""
        return session.get('zoho_refresh_token')
    
    def refresh_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        refresh_token = self.get_refresh_token()
        if not refresh_token:
            current_app.logger.error("No refresh token available")
            return False
        
        try:
            # Use EU domain for token refresh
            response = requests.post(
                "https://accounts.zoho.eu/oauth/v2/token",
                data={
                    'refresh_token': refresh_token,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'grant_type': 'refresh_token'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' not in data:
                    current_app.logger.error(f"Invalid refresh token response: {data}")
                    return False
                    
                session['zoho_access_token'] = data['access_token']
                session['zoho_token_expires_at'] = int(time.time() + data.get('expires_in', 3600))
                session.modified = True
                current_app.logger.info("Successfully refreshed access token")
                return True
                
            current_app.logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error refreshing Zoho token: {str(e)}")
            return False
    
    def get_inventory(self) -> Optional[List[Dict[str, Any]]]:
        """Get inventory data from Zoho."""
        access_token = self.get_access_token()
        if not access_token:
            current_app.logger.error("No access token available")
            return None
            
        try:
            current_app.logger.info("Fetching inventory data from Zoho")
            
            # Add filter for active items
            response = requests.get(
                f"{self.base_url}/items",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                params={
                    'status': 'active'  # Only fetch active items
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                current_app.logger.info(f"Successfully fetched {len(items)} active items from Zoho")
                return items
            elif response.status_code == 401:
                current_app.logger.info("Token expired, attempting to refresh")
                if self.refresh_token():
                    return self.get_inventory()
            
            current_app.logger.error(f"Failed to fetch inventory from Zoho: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error fetching inventory from Zoho: {str(e)}")
            return None
    
    def sync_inventory(self, user: User) -> bool:
        """Sync inventory with Zoho."""
        try:
            # Get items from Zoho
            zoho_items = self.get_inventory()
            if not zoho_items:
                return False

            # Get existing items from database
            existing_items = Item.query.filter_by(user_id=user.id).all()
            existing_zoho_ids = {item.zoho_item_id for item in existing_items if item.zoho_item_id}
            
            # Get current date for expiry comparison
            current_date = datetime.now().date()
            
            # Update existing items
            for item in existing_items:
                if item.zoho_item_id:
                    zoho_item = next((zi for zi in zoho_items if zi['item_id'] == item.zoho_item_id), None)
                    if zoho_item:
                        # Update item details from Zoho
                        item.name = zoho_item['name']
                        item.description = zoho_item.get('description', '')
                        item.unit = zoho_item.get('unit', '')
                        item.selling_price = float(zoho_item.get('rate', 0))
                        item.quantity = float(zoho_item.get('stock_on_hand', 0))
                        
                        # Handle Zoho status changes
                        zoho_status = zoho_item.get('status', 'active')
                        if zoho_status == 'inactive':
                            # If item is inactive in Zoho, set expiry date to current date
                            item.expiry_date = current_date
                            item.status = 'Expired'
                        else:
                            # If item is active in Zoho, only update expiry date if it exists in Zoho
                            if 'expiry_date' in zoho_item:
                                try:
                                    item.expiry_date = datetime.strptime(zoho_item['expiry_date'], '%Y-%m-%d').date()
                                    # Update status based on expiry date
                                    days_until_expiry = (item.expiry_date - current_date).days
                                    if days_until_expiry < 0:
                                        item.status = 'Expired'
                                    elif days_until_expiry <= 30:
                                        item.status = 'Expiring Soon'
                                    else:
                                        item.status = 'Active'
                                except ValueError:
                                    current_app.logger.warning(f"Invalid expiry date format for item {item.id}: {zoho_item['expiry_date']}")
                            # Don't change expiry date or status if not provided in Zoho
                        
                        existing_zoho_ids.remove(item.zoho_item_id)
                    else:
                        # Item exists in local DB but not in Zoho
                        item.zoho_item_id = None
                        item.status = 'Pending Expiry Date'
                else:
                    # Local item without Zoho ID
                    item.status = 'Pending Expiry Date'
            
            # Add new items from Zoho
            for zoho_item in zoho_items:
                zoho_item_id = zoho_item['item_id']
                if zoho_item_id not in existing_zoho_ids:
                    # Check if item already exists with this Zoho ID
                    existing_item = Item.query.filter_by(zoho_item_id=zoho_item_id).first()
                    if existing_item:
                        # Update existing item
                        existing_item.name = zoho_item['name']
                        existing_item.description = zoho_item.get('description', '')
                        existing_item.unit = zoho_item.get('unit', '')
                        existing_item.selling_price = float(zoho_item.get('rate', 0))
                        existing_item.quantity = float(zoho_item.get('stock_on_hand', 0))
                        
                        # Handle Zoho status changes
                        zoho_status = zoho_item.get('status', 'active')
                        if zoho_status == 'inactive':
                            existing_item.expiry_date = current_date
                            existing_item.status = 'Expired'
                        else:
                            # If item is active in Zoho, only update expiry date if it exists in Zoho
                            if 'expiry_date' in zoho_item:
                                try:
                                    existing_item.expiry_date = datetime.strptime(zoho_item['expiry_date'], '%Y-%m-%d').date()
                                    # Update status based on expiry date
                                    days_until_expiry = (existing_item.expiry_date - current_date).days
                                    if days_until_expiry < 0:
                                        existing_item.status = 'Expired'
                                    elif days_until_expiry <= 30:
                                        existing_item.status = 'Expiring Soon'
                                    else:
                                        existing_item.status = 'Active'
                                except ValueError:
                                    current_app.logger.warning(f"Invalid expiry date format for item {existing_item.id}: {zoho_item['expiry_date']}")
                            # Don't change expiry date or status if not provided in Zoho
                    else:
                        # Create new item
                        item = Item(
                            name=zoho_item['name'],
                            description=zoho_item.get('description', ''),
                            quantity=float(zoho_item.get('stock_on_hand', 0)),
                            unit=zoho_item.get('unit', ''),
                            selling_price=float(zoho_item.get('rate', 0)),
                            zoho_item_id=zoho_item_id,
                            user_id=user.id
                        )
                        
                        # Handle Zoho status and expiry date
                        zoho_status = zoho_item.get('status', 'active')
                        if zoho_status == 'inactive':
                            item.expiry_date = current_date
                            item.status = 'Expired'
                        else:
                            # If item is active in Zoho, only update expiry date if it exists in Zoho
                            if 'expiry_date' in zoho_item:
                                try:
                                    item.expiry_date = datetime.strptime(zoho_item['expiry_date'], '%Y-%m-%d').date()
                                    # Update status based on expiry date
                                    days_until_expiry = (item.expiry_date - current_date).days
                                    if days_until_expiry < 0:
                                        item.status = 'Expired'
                                    elif days_until_expiry <= 30:
                                        item.status = 'Expiring Soon'
                                    else:
                                        item.status = 'Active'
                                except ValueError:
                                    current_app.logger.warning(f"Invalid expiry date format for new item: {zoho_item['expiry_date']}")
                            # Don't change expiry date or status if not provided in Zoho
                        
                        db.session.add(item)
            
            db.session.commit()
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error syncing inventory: {str(e)}")
            db.session.rollback()
            return False
    
    def get_auth_url(self) -> str:
        """Generate Zoho OAuth authorization URL."""
        # Use EU domain since we're getting redirected there
        auth_url = "https://accounts.zoho.eu/oauth/v2/auth"
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': 'ZohoInventory.items.ALL,ZohoInventory.settings.ALL',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        
        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        return f"{auth_url}?{query_string}"
    
    def handle_callback(self, code: str) -> bool:
        """Handle OAuth callback from Zoho."""
        try:
            # Get the location from the callback URL
            location = request.args.get('location', 'com')
            accounts_server = request.args.get('accounts-server', 'https://accounts.zoho.com')
            
            # Use the correct token endpoint based on location
            token_url = f"{accounts_server}/oauth/v2/token"
            
            current_app.logger.info(f"Requesting token from: {token_url}")
            
            response = requests.post(
                token_url,
                data={
                    'code': code,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'redirect_uri': self.redirect_uri,
                    'grant_type': 'authorization_code'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                current_app.logger.info(f"Received token response: {data}")
                
                if 'access_token' not in data:
                    current_app.logger.error(f"Invalid response from Zoho: {data}")
                    return False
                    
                session['zoho_access_token'] = data['access_token']
                session['zoho_refresh_token'] = data.get('refresh_token')
                session['zoho_token_expires_at'] = int(time.time() + data.get('expires_in', 3600))
                session.modified = True
                
                current_app.logger.info("Successfully stored tokens in session")
                return True
            else:
                current_app.logger.error(f"Failed to get token from Zoho: {response.text}")
                return False
            
        except Exception as e:
            current_app.logger.error(f"Error handling Zoho callback: {str(e)}")
            return False

    def get_item_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an item from Zoho by name."""
        access_token = self.get_access_token()
        if not access_token:
            current_app.logger.error("No access token available")
            return None
            
        try:
            # First try to find active items
            response = requests.get(
                f"{self.base_url}/items",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                params={
                    'name': name,
                    'status': 'active'  # Check active items first
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                if items:
                    current_app.logger.info(f"Found active item with name '{name}' in Zoho")
                    return items[0]
            
            # If no active items found, check inactive items
            response = requests.get(
                f"{self.base_url}/items",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                params={
                    'name': name,
                    'status': 'inactive'  # Check inactive items
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                if items:
                    current_app.logger.info(f"Found inactive item with name '{name}' in Zoho")
                    return items[0]
            
            current_app.logger.info(f"No items found with name '{name}' in Zoho")
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error getting item from Zoho: {str(e)}")
            return None

    def create_item_in_zoho(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new item in Zoho Inventory."""
        access_token = self.get_access_token()
        if not access_token:
            current_app.logger.error("No access token available")
            return None
            
        try:
            current_app.logger.info(f"Creating item in Zoho with status: {item_data.get('status', 'active')}")
            
            # Check if item already exists in Zoho (both active and inactive)
            existing_item = self.get_item_by_name(item_data['name'])
            if existing_item:
                if existing_item.get('status') == 'inactive':
                    current_app.logger.info(f"Found inactive item '{item_data['name']}' in Zoho. Reactivating it.")
                    # Reactivate the item
                    response = requests.put(
                        f"{self.base_url}/items/{existing_item['item_id']}",
                        headers={
                            'Authorization': f'Bearer {access_token}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            "status": "active",
                            "name": item_data['name'],
                            "unit": item_data['unit'],
                            "rate": float(item_data['selling_price']),
                            "description": item_data.get('description', ''),
                            "stock_on_hand": float(item_data['quantity'])
                        }
                    )
                    
                    if response.status_code == 200:
                        current_app.logger.info(f"Successfully reactivated item in Zoho: {existing_item['item_id']}")
                        return existing_item
                    else:
                        current_app.logger.error(f"Failed to reactivate item in Zoho: {response.status_code} - {response.text}")
                else:
                    current_app.logger.info(f"Item '{item_data['name']}' already exists in Zoho. Linking to existing item.")
                    return existing_item
            
            # Determine status based on expiry date
            expiry_date = datetime.strptime(item_data['expiry_date'], '%Y-%m-%d').date()
            current_date = datetime.now().date()
            status = "inactive" if expiry_date <= current_date else "active"
            
            # Create item with only essential fields
            request_data = {
                "name": item_data['name'],
                "unit": item_data['unit'],
                "rate": float(item_data['selling_price']),
                "description": item_data.get('description', ''),
                "status": status,
                "item_type": "inventory",
                "product_type": "goods"
            }
            
            # Add stock information
            if item_data.get('quantity'):
                request_data["initial_stock"] = float(item_data['quantity'])
                if item_data.get('cost_price'):
                    request_data["initial_stock_rate"] = float(item_data['cost_price'])
            
            current_app.logger.info(f"Creating item in Zoho with data: {request_data}")
            
            response = requests.post(
                f"{self.base_url}/items",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=request_data
            )
            
            if response.status_code == 201:
                data = response.json()
                current_app.logger.info(f"Successfully created item in Zoho: {data}")
                return data.get('item')
            elif response.status_code == 401:
                current_app.logger.info("Token expired, attempting to refresh")
                if self.refresh_token():
                    return self.create_item_in_zoho(item_data)
            
            current_app.logger.error(f"Failed to create item in Zoho: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error creating item in Zoho: {str(e)}")
            return None

    def update_item_in_zoho(self, zoho_item_id: str, item_data: Dict[str, Any]) -> bool:
        """Update an existing item in Zoho Inventory."""
        access_token = self.get_access_token()
        if not access_token:
            current_app.logger.error("No access token available")
            return False
        
        try:
            current_app.logger.info(f"Updating item {zoho_item_id} in Zoho")
            
            # Determine status based on expiry date
            expiry_date = datetime.strptime(item_data['expiry_date'], '%Y-%m-%d').date()
            current_date = datetime.now().date()
            status = "inactive" if expiry_date <= current_date else "active"
            
            # Prepare the update data
            update_data = {
                "name": item_data['name'],
                "unit": item_data['unit'],
                "stock_on_hand": item_data['quantity'],
                "description": item_data.get('description', ''),
                "status": status
            }
            
            # Only include rate if selling_price is provided
            if 'selling_price' in item_data and item_data['selling_price'] is not None:
                update_data["rate"] = float(item_data['selling_price'])
            
            response = requests.put(
                f"{self.base_url}/items/{zoho_item_id}",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=update_data
            )
            
            if response.status_code == 200:
                current_app.logger.info(f"Successfully updated item {zoho_item_id} in Zoho with status: {status}")
                return True
            elif response.status_code == 401:
                current_app.logger.info("Token expired, attempting to refresh")
                if self.refresh_token():
                    return self.update_item_in_zoho(zoho_item_id, item_data)
            
            current_app.logger.error(f"Failed to update item in Zoho: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error updating item in Zoho: {str(e)}")
            return False

    def delete_item_in_zoho(self, zoho_item_id: str) -> bool:
        """Mark an item as inactive in Zoho Inventory."""
        access_token = self.get_access_token()
        if not access_token:
            current_app.logger.error("No access token available")
            return False
        
        try:
            current_app.logger.info(f"Marking item {zoho_item_id} as inactive in Zoho")
            response = requests.put(
                f"{self.base_url}/items/{zoho_item_id}",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json={
                    "status": "inactive"
                }
            )
            
            if response.status_code == 200:
                current_app.logger.info(f"Successfully marked item {zoho_item_id} as inactive in Zoho")
                return True
            elif response.status_code == 401:
                current_app.logger.info("Token expired, attempting to refresh")
                if self.refresh_token():
                    return self.delete_item_in_zoho(zoho_item_id)
            
            current_app.logger.error(f"Failed to mark item as inactive in Zoho: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error marking item as inactive in Zoho: {str(e)}")
            return False

    def check_and_update_expired_items(self, user: User) -> bool:
        """Check for expired items and update their status in Zoho."""
        try:
            # Get all items for the user
            items = Item.query.filter_by(user_id=user.id).all()
            current_date = datetime.now().date()
            
            for item in items:
                if not item.zoho_item_id or not item.expiry_date:
                    continue
                    
                # Check if item has expired
                if item.expiry_date.date() <= current_date:
                    # Update item status in Zoho to inactive
                    self.update_item_in_zoho(item.zoho_item_id, {
                        "name": item.name,
                        "unit": item.unit,
                        "rate": item.selling_price,
                        "stock_on_hand": item.quantity,
                        "description": item.description or "",
                        "expiry_date": item.expiry_date.strftime('%Y-%m-%d'),
                        "status": "inactive"
                    })
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error checking expired items: {str(e)}")
            return False

    def get_item_status(self, zoho_item_id: str) -> Optional[str]:
        """Get the status of an item in Zoho Inventory."""
        access_token = self.get_access_token()
        if not access_token:
            current_app.logger.error("No access token available")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/items/{zoho_item_id}",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('item', {}).get('status')
            elif response.status_code == 401:
                current_app.logger.info("Token expired, attempting to refresh")
                if self.refresh_token():
                    return self.get_item_status(zoho_item_id)
            
            current_app.logger.error(f"Failed to get item status from Zoho: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error getting item status from Zoho: {str(e)}")
            return None 