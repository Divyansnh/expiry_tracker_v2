# Product Inventory & Expiry Tracking System

A Flask-based web application for managing product inventory and tracking expiry dates. The system integrates with Zoho for inventory management and provides features like OCR-based expiry date extraction, notifications, and analytics.

## Features

- User authentication and authorization
- Inventory management with expiry date tracking
- OCR-based expiry date extraction from images
- Email and SMS notifications for expiring items
- Integration with Zoho for inventory sync
- Analytics and reporting
- Mobile-responsive design

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Zoho account for inventory integration
- Twilio account for SMS notifications (optional)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/expiry_tracker_v2.git
cd expiry_tracker_v2
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
flask db upgrade
```

## Configuration

The application can be configured through environment variables in the `.env` file:

- `FLASK_APP`: Application entry point
- `FLASK_ENV`: Environment (development/production)
- `DATABASE_URL`: PostgreSQL database URL
- `SECRET_KEY`: Application secret key
- `ZOHO_CLIENT_ID`: Zoho OAuth client ID
- `ZOHO_CLIENT_SECRET`: Zoho OAuth client secret
- `ZOHO_REDIRECT_URI`: Zoho OAuth redirect URI
- `TWILIO_ACCOUNT_SID`: Twilio account SID (optional)
- `TWILIO_AUTH_TOKEN`: Twilio auth token (optional)
- `TWILIO_PHONE_NUMBER`: Twilio phone number (optional)

## Usage

1. Start the development server:
```bash
flask run
```

2. Access the application at `http://localhost:5000`

3. Register a new account or log in with existing credentials

4. Connect your Zoho account for inventory sync

5. Start managing your inventory and tracking expiry dates

## Development

### Project Structure

```
expiry_tracker_v2/
├── app/
│   ├── api/           # API endpoints
│   ├── core/          # Core functionality
│   ├── models/        # Database models
│   ├── routes/        # Web routes
│   ├── services/      # Business logic
│   ├── static/        # Static files
│   └── templates/     # HTML templates
├── migrations/        # Database migrations
├── tests/            # Test suite
├── .env              # Environment variables
├── .gitignore        # Git ignore file
├── alembic.ini       # Alembic configuration
├── config.py         # Application configuration
├── requirements.txt  # Python dependencies
└── run.py           # Application entry point
```

### Running Tests

```bash
pytest
```

### Code Style

The project follows PEP 8 guidelines. Format code using:

```bash
black .
```

### Database Migrations

Create a new migration:
```bash
flask db migrate -m "description"
```

Apply migrations:
```bash
flask db upgrade
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 