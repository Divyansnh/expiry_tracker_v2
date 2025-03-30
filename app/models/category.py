from app.core.extensions import db
from app.models.base import BaseModel

class Category(BaseModel):
    """Category model for item categorization."""
    
    __tablename__ = 'categories'
    
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    def to_dict(self):
        """Convert category to dictionary."""
        data = super().to_dict()
        data.update({
            'name': self.name,
            'description': self.description
        })
        return data
    
    def __repr__(self):
        """String representation of the category."""
        return f'<Category {self.name}>' 