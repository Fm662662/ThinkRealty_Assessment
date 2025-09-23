# db/base_class.py
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from datetime import datetime
from sqlalchemy import Column, DateTime

@as_declarative()
class Base:
    id: any
    __name__: str

    # Generate __tablename__ automatically if not provided
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # Optional timestamps for all tables
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
