import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.services.ocr_service import OCRService
import os

@pytest.fixture
def ocr_service():
    """Create an OCR service instance."""
    return OCRService()

@pytest.fixture
def sample_image_path(tmp_path):
    """Create a sample image file."""
    image_path = tmp_path / "test_image.jpg"
    image_path.write_bytes(b"fake image data")
    return str(image_path)

def test_validate_date(ocr_service):
    """Test date validation."""
    # Valid dates
    assert ocr_service.validate_date("2024-12-31")
    assert ocr_service.validate_date("31/12/2024")
    assert ocr_service.validate_date("31-12-2024")
    
    # Invalid dates
    assert not ocr_service.validate_date("2024-13-31")  # Invalid month
    assert not ocr_service.validate_date("2024-12-32")  # Invalid day
    assert not ocr_service.validate_date("invalid date")

def test_extract_date_from_text(ocr_service):
    """Test date extraction from text."""
    # Test various date formats
    text = """
    Expiry Date: 31/12/2024
    Best Before: 2024-12-31
    Use By: 31-12-2024
    """
    
    dates = ocr_service._extract_date_from_text(text)
    assert len(dates) == 3
    assert all(ocr_service.validate_date(date) for date in dates)

def test_extract_date_from_text_no_dates(ocr_service):
    """Test text without dates."""
    text = "This is a sample text without any dates."
    dates = ocr_service._extract_date_from_text(text)
    assert len(dates) == 0

@patch('app.services.ocr_service.easyocr.Reader')
def test_read_image_success(mock_reader, ocr_service, sample_image_path):
    """Test successful image reading."""
    # Mock EasyOCR response
    mock_reader.return_value.readtext.return_value = [
        ([[0, 0], [100, 0], [100, 50], [0, 50]], "Expiry Date: 31/12/2024", 0.95)
    ]
    
    # Test image reading
    text = ocr_service._read_image(sample_image_path)
    assert text == "Expiry Date: 31/12/2024"
    mock_reader.return_value.readtext.assert_called_once()

@patch('app.services.ocr_service.easyocr.Reader')
def test_read_image_failure(mock_reader, ocr_service, sample_image_path):
    """Test failed image reading."""
    # Mock EasyOCR error
    mock_reader.return_value.readtext.side_effect = Exception("OCR error")
    
    # Test image reading
    with pytest.raises(Exception):
        ocr_service._read_image(sample_image_path)

def test_process_image_success(ocr_service, sample_image_path):
    """Test successful image processing."""
    with patch.object(ocr_service, '_read_image') as mock_read:
        with patch.object(ocr_service, '_extract_date_from_text') as mock_extract:
            # Mock the responses
            mock_read.return_value = "Expiry Date: 31/12/2024"
            mock_extract.return_value = ["31/12/2024"]
            
            # Process image
            result = ocr_service.process_image(sample_image_path)
            
            assert result is not None
            assert 'expiry_date' in result
            assert result['expiry_date'] == "31/12/2024"
            assert 'confidence' in result
            assert 'text' in result

def test_process_image_no_date(ocr_service, sample_image_path):
    """Test image processing without date."""
    with patch.object(ocr_service, '_read_image') as mock_read:
        with patch.object(ocr_service, '_extract_date_from_text') as mock_extract:
            # Mock the responses
            mock_read.return_value = "No date in this text"
            mock_extract.return_value = []
            
            # Process image
            result = ocr_service.process_image(sample_image_path)
            
            assert result is not None
            assert 'expiry_date' not in result
            assert 'text' in result

def test_process_image_invalid_file(ocr_service):
    """Test processing invalid file."""
    with pytest.raises(Exception):
        ocr_service.process_image("nonexistent_file.jpg")

def test_process_image_invalid_date(ocr_service, sample_image_path):
    """Test image processing with invalid date."""
    with patch.object(ocr_service, '_read_image') as mock_read:
        with patch.object(ocr_service, '_extract_date_from_text') as mock_extract:
            # Mock the responses
            mock_read.return_value = "Invalid date: 32/13/2024"
            mock_extract.return_value = ["32/13/2024"]
            
            # Process image
            result = ocr_service.process_image(sample_image_path)
            
            assert result is not None
            assert 'expiry_date' not in result
            assert 'text' in result

def test_process_image_multiple_dates(ocr_service, sample_image_path):
    """Test image processing with multiple dates."""
    with patch.object(ocr_service, '_read_image') as mock_read:
        with patch.object(ocr_service, '_extract_date_from_text') as mock_extract:
            # Mock the responses
            mock_read.return_value = "Expiry: 31/12/2024, Best Before: 30/12/2024"
            mock_extract.return_value = ["31/12/2024", "30/12/2024"]
            
            # Process image
            result = ocr_service.process_image(sample_image_path)
            
            assert result is not None
            assert 'expiry_date' in result
            assert result['expiry_date'] == "31/12/2024"  # Should use the first valid date 