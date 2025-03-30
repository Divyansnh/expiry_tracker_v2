"""API v1 package."""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

from app.api.v1 import auth, inventory, notifications, ocr 