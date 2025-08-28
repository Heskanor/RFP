"""
Vendor Service - Handles vendor-related business logic
"""
from typing import Dict, List, Optional
from app.config.database import get_db_connection
from app.models.models import Collections
from app.config.defaults import get_available_model
from app.config.llm_factory import LLMFactory
import uuid
from datetime import datetime

async def get_vendors(project_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get all vendors, optionally filtered by project."""
    try:
        db = get_db_connection()
        vendors_ref = db.child(Collections.VENDOR.value)
        
        if project_id:
            # Filter vendors by project association
            # This would require a separate collection or field to track project-vendor relationships
            vendors = vendors_ref.order_by_key().limit_to_first(limit).get()
        else:
            vendors = vendors_ref.order_by_key().limit_to_first(limit).get()
        
        if vendors.val():
            return [{"id": k, **v} for k, v in vendors.val().items()]
        return []
    except Exception as e:
        print(f"Error getting vendors: {e}")
        return []

async def get_vendor(vendor_id: str) -> Optional[Dict]:
    """Get vendor by ID."""
    try:
        db = get_db_connection()
        vendor = db.child(Collections.VENDOR.value).child(vendor_id).get()
        
        if vendor.val():
            return {"id": vendor_id, **vendor.val()}
        return None
    except Exception as e:
        print(f"Error getting vendor {vendor_id}: {e}")
        return None

async def create_vendor(vendor_data: Dict) -> Dict:
    """Create a new vendor."""
    try:
        db = get_db_connection()
        vendor_id = str(uuid.uuid4())
        
        vendor = {
            "id": vendor_id,
            "name": vendor_data.get("name"),
            "email": vendor_data.get("email"),
            "headquarters": vendor_data.get("headquarters"),
            "employees": vendor_data.get("employees"),
            "annual_revenue": vendor_data.get("annual_revenue"),
            "description": vendor_data.get("description", ""),
            "created_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp())
        }
        
        db.child(Collections.VENDOR.value).child(vendor_id).set(vendor)
        return vendor
    except Exception as e:
        print(f"Error creating vendor: {e}")
        raise e

async def update_vendor(vendor_id: str, vendor_data: Dict) -> Optional[Dict]:
    """Update vendor information."""
    try:
        db = get_db_connection()
        
        # Check if vendor exists
        existing_vendor = await get_vendor(vendor_id)
        if not existing_vendor:
            return None
        
        # Update fields
        updated_data = {
            **vendor_data,
            "updated_at": int(datetime.now().timestamp())
        }
        
        db.child(Collections.VENDOR.value).child(vendor_id).update(updated_data)
        
        # Return updated vendor
        return await get_vendor(vendor_id)
    except Exception as e:
        print(f"Error updating vendor {vendor_id}: {e}")
        raise e

async def delete_vendor(vendor_id: str) -> bool:
    """Delete a vendor."""
    try:
        db = get_db_connection()
        
        # Check if vendor exists
        existing_vendor = await get_vendor(vendor_id)
        if not existing_vendor:
            return False
        
        db.child(Collections.VENDOR.value).child(vendor_id).remove()
        return True
    except Exception as e:
        print(f"Error deleting vendor {vendor_id}: {e}")
        return False
