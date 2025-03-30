import os
import re
from datetime import datetime
from typing import Optional, Dict, Any
from flask import current_app
import easyocr
from PIL import Image

class OCRService:
    """Service for handling OCR operations."""
    
    def __init__(self):
        self.reader = easyocr.Reader(['en'])
        self.date_patterns = [
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',    # YYYY/MM/DD or YYYY-MM-DD
            r'(\d{1,2})\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{2,4})',  # DD MMM YYYY
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{2,4})'  # MMM DD, YYYY
        ]
    
    def extract_date_from_image(self, image_path: str) -> Optional[datetime]:
        """Extract expiry date from an image."""
        try:
            # Read the image
            results = self.reader.readtext(image_path)
            
            # Extract text from results
            text = ' '.join([result[1] for result in results])
            
            # Look for date patterns
            for pattern in self.date_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        if len(match.groups()) == 3:
                            # Handle different date formats
                            if len(match.group(3)) == 4:  # Full year
                                year = int(match.group(3))
                            else:  # Two-digit year
                                year = 2000 + int(match.group(3))
                            
                            if len(match.group(1)) == 4:  # YYYY-MM-DD format
                                date = datetime(year, int(match.group(2)), int(match.group(3)))
                            else:  # DD-MM-YYYY format
                                date = datetime(year, int(match.group(2)), int(match.group(1)))
                            
                            # Validate date
                            if self._is_valid_date(date):
                                return date
                    except (ValueError, IndexError):
                        continue
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error extracting date from image: {str(e)}")
            return None
    
    def _is_valid_date(self, date: datetime) -> bool:
        """Validate extracted date."""
        today = datetime.now()
        
        # Date should not be in the past
        if date < today:
            return False
        
        # Date should not be too far in the future (e.g., 10 years)
        max_future = today.replace(year=today.year + 10)
        if date > max_future:
            return False
        
        return True
    
    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Process an image and extract relevant information."""
        try:
            # Validate image
            if not self._validate_image(image_path):
                return {
                    'success': False,
                    'error': 'Invalid image format or size'
                }
            
            # Extract date
            expiry_date = self.extract_date_from_image(image_path)
            
            if not expiry_date:
                return {
                    'success': False,
                    'error': 'No valid expiry date found in image'
                }
            
            return {
                'success': True,
                'expiry_date': expiry_date.isoformat(),
                'confidence': 'high'  # You could implement confidence scoring
            }
            
        except Exception as e:
            current_app.logger.error(f"Error processing image: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_image(self, image_path: str) -> bool:
        """Validate image format and size."""
        try:
            # Check file size
            if os.path.getsize(image_path) > current_app.config['MAX_CONTENT_LENGTH']:
                return False
            
            # Check image format
            with Image.open(image_path) as img:
                if img.format.lower() not in current_app.config['ALLOWED_EXTENSIONS']:
                    return False
                
                # Check image dimensions
                if img.size[0] > 5000 or img.size[1] > 5000:  # Max 5000x5000 pixels
                    return False
            
            return True
            
        except Exception:
            return False 