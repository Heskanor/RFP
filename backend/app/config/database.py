"""
Database configuration - provides fallback when Firebase is not configured
"""
import os
from typing import Dict, Any, Optional

# Try to import Firebase, but gracefully handle missing config
try:
    from app.config.firebase import firebase_manager
    FIREBASE_AVAILABLE = True
except Exception as e:
    print(f"Firebase not configured: {e}")
    FIREBASE_AVAILABLE = False
    firebase_manager = None

class MockDatabase:
    """Mock database for testing when Firebase is not available"""
    
    def __init__(self):
        self._data = {}
    
    def child(self, path: str):
        """Return a mock reference"""
        return MockReference(self._data, path)

class MockReference:
    """Mock Firebase reference"""
    
    def __init__(self, data: dict, path: str):
        self._data = data
        self._path = path
        
    def child(self, subpath: str):
        full_path = f"{self._path}/{subpath}"
        return MockReference(self._data, full_path)
    
    def get(self):
        """Mock get operation"""
        return MockSnapshot(self._data.get(self._path))
    
    def set(self, data: dict):
        """Mock set operation"""
        self._data[self._path] = data
        return True
    
    def update(self, data: dict):
        """Mock update operation"""
        if self._path in self._data:
            self._data[self._path].update(data)
        else:
            self._data[self._path] = data
        return True
    
    def remove(self):
        """Mock remove operation"""
        if self._path in self._data:
            del self._data[self._path]
        return True
    
    def order_by_key(self):
        return self
    
    def limit_to_first(self, limit: int):
        return self

class MockSnapshot:
    """Mock Firebase snapshot"""
    
    def __init__(self, data):
        self._data = data
    
    def val(self):
        return self._data

def get_db_connection():
    """Get database connection - Firebase if available, mock if not"""
    if FIREBASE_AVAILABLE and firebase_manager:
        return firebase_manager.db
    else:
        print("Using mock database for testing (Firebase not configured)")
        return MockDatabase()



