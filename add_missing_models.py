#!/usr/bin/env python3
"""
Add missing models to database.py
"""
import re

def add_missing_models():
    # Read the current database.py
    with open('database.py', 'r') as f:
        content = f.read()
    
    # Add the missing models after the existing models import
    models_to_add = '''
# Additional models that were missing
class Campaign(Base):
    """Campaign model for content campaigns"""
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    description = Column(Text)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
class RawData(Base):
    """Raw data model for storing unprocessed content"""
    __tablename__ = "raw_data"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    source = Column(String(255))
    platform = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    
class MachineContent(Base):
    """Machine-generated content model"""
    __tablename__ = "machine_content"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    content = Column(Text)
    platform = Column(String(100))
    status = Column(String(50), default="generated")
    created_at = Column(DateTime, default=datetime.utcnow)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    raw_data_id = Column(Integer, ForeignKey("raw_data.id"))
'''
    
    # Add the necessary imports
    imports_to_add = '''
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
'''
    
    # Add imports after the existing imports
    content = content.replace('from sqlalchemy.orm import sessionmaker, Session', 
                            'from sqlalchemy.orm import sessionmaker, Session' + imports_to_add)
    
    # Add models after the existing class definitions
    content = content.replace('logger.info("Database module loaded successfully")', 
                            models_to_add + '\nlogger.info("Database module loaded successfully")')
    
    # Update the __all__ export
    content = content.replace('__all__ = ["engine", "SessionLocal", "Base", "DatabaseManager", "DatabaseManager1", "Agent", "Task", "db_manager"]',
                            '__all__ = ["engine", "SessionLocal", "Base", "DatabaseManager", "DatabaseManager1", "Agent", "Task", "Campaign", "RawData", "MachineContent", "db_manager"]')
    
    # Write the updated content
    with open('database.py', 'w') as f:
        f.write(content)
    
    print("✅ Added missing models: Campaign, RawData, MachineContent")
    print("✅ Updated imports and exports")

if __name__ == "__main__":
    add_missing_models()
