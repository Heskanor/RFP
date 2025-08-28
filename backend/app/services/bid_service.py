"""
Bid Service - Handles bid submissions and document management
"""
from typing import Dict, List, Optional
from fastapi import UploadFile
from app.config.database import get_db_connection
from app.models.models import Collections
from app.config.defaults import get_available_model
from app.config.llm_factory import LLMFactory
import uuid
from datetime import datetime

async def get_bids(
    project_id: Optional[str] = None,
    vendor_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict]:
    """Get bids with optional filtering."""
    try:
        db = get_db_connection()
        bids_ref = db.child(Collections.BID.value if hasattr(Collections, 'BID') else "bids")
        
        # For now, get all bids and filter in memory
        # In production, implement proper database filtering
        bids = bids_ref.order_by_key().limit_to_first(limit).get()
        
        if bids.val():
            bid_list = [{"id": k, **v} for k, v in bids.val().items()]
            
            # Apply filters
            if project_id:
                bid_list = [b for b in bid_list if b.get("project_id") == project_id]
            if vendor_id:
                bid_list = [b for b in bid_list if b.get("vendor_id") == vendor_id]
            if status:
                bid_list = [b for b in bid_list if b.get("status") == status]
            
            return bid_list
        return []
    except Exception as e:
        print(f"Error getting bids: {e}")
        return []

async def get_bid(bid_id: str) -> Optional[Dict]:
    """Get bid by ID."""
    try:
        db = get_db_connection()
        bid = db.child(Collections.BID.value if hasattr(Collections, 'BID') else "bids").child(bid_id).get()
        
        if bid.val():
            return {"id": bid_id, **bid.val()}
        return None
    except Exception as e:
        print(f"Error getting bid {bid_id}: {e}")
        return None

async def create_bid(bid_data: Dict) -> Dict:
    """Create a new bid submission."""
    try:
        db = get_db_connection()
        bid_id = str(uuid.uuid4())
        
        bid = {
            "id": bid_id,
            "project_id": bid_data.get("project_id"),
            "vendor_id": bid_data.get("vendor_id"),
            "title": bid_data.get("title", ""),
            "summary": bid_data.get("summary", ""),
            "total_cost": bid_data.get("total_cost", 0),
            "currency": bid_data.get("currency", "USD"),
            "delivery_timeline": bid_data.get("delivery_timeline", ""),
            "status": bid_data.get("status", "submitted"),
            "documents": [],
            "ai_analysis": {},
            "created_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp())
        }
        
        # Use Gemini to analyze bid content
        if bid_data.get("summary"):
            model = get_available_model("analysis")
            llm = LLMFactory.get_llm(model, temperature=0.1)
            
            analysis_prompt = f"""
            Analyze this RFP bid submission and provide insights:
            
            Title: {bid.get('title')}
            Summary: {bid.get('summary')}
            Cost: {bid.get('total_cost')} {bid.get('currency')}
            Timeline: {bid.get('delivery_timeline')}
            
            Provide analysis on:
            1. Strengths and weaknesses
            2. Cost competitiveness assessment
            3. Timeline feasibility
            4. Key risks to consider
            5. Overall recommendation
            
            Format as JSON with keys: strengths, weaknesses, cost_analysis, timeline_analysis, risks, recommendation
            """
            
            try:
                # Simple analysis - in production, use structured output
                analysis_response = await llm.ainvoke(analysis_prompt)
                bid["ai_analysis"] = {
                    "analysis": analysis_response.content,
                    "analyzed_at": int(datetime.now().timestamp())
                }
            except Exception as ai_error:
                print(f"AI analysis failed: {ai_error}")
                bid["ai_analysis"] = {"error": "Analysis failed"}
        
        db.child(Collections.BID.value if hasattr(Collections, 'BID') else "bids").child(bid_id).set(bid)
        return bid
    except Exception as e:
        print(f"Error creating bid: {e}")
        raise e

async def update_bid(bid_id: str, bid_data: Dict) -> Optional[Dict]:
    """Update bid information."""
    try:
        db = get_db_connection()
        
        # Check if bid exists
        existing_bid = await get_bid(bid_id)
        if not existing_bid:
            return None
        
        # Update fields
        updated_data = {
            **bid_data,
            "updated_at": int(datetime.now().timestamp())
        }
        
        db.child(Collections.BID.value if hasattr(Collections, 'BID') else "bids").child(bid_id).update(updated_data)
        
        # Return updated bid
        return await get_bid(bid_id)
    except Exception as e:
        print(f"Error updating bid {bid_id}: {e}")
        raise e

async def delete_bid(bid_id: str) -> bool:
    """Delete a bid."""
    try:
        db = get_db_connection()
        
        # Check if bid exists
        existing_bid = await get_bid(bid_id)
        if not existing_bid:
            return False
        
        db.child(Collections.BID.value if hasattr(Collections, 'BID') else "bids").child(bid_id).remove()
        return True
    except Exception as e:
        print(f"Error deleting bid {bid_id}: {e}")
        return False

async def upload_bid_document(bid_id: str, file: UploadFile, document_type: str = "proposal") -> Dict:
    """Upload a document for a bid."""
    try:
        # Check if bid exists
        existing_bid = await get_bid(bid_id)
        if not existing_bid:
            raise ValueError("Bid not found")
        
        # In production, upload to cloud storage (S3, Firebase Storage, etc.)
        # For now, create a document record
        document_id = str(uuid.uuid4())
        document = {
            "id": document_id,
            "bid_id": bid_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file.size if hasattr(file, 'size') else 0,
            "document_type": document_type,
            "upload_url": f"/documents/{document_id}",  # Placeholder
            "uploaded_at": int(datetime.now().timestamp())
        }
        
        # Read file content for AI analysis
        content = await file.read()
        
        # Use Gemini to analyze document content (if text-based)
        if document_type in ["proposal", "technical"] and file.content_type in ["text/plain", "application/pdf"]:
            model = get_available_model("extraction")
            llm = LLMFactory.get_llm(model, temperature=0.1)
            
            analysis_prompt = f"""
            Analyze this bid document and extract key information:
            
            Document Type: {document_type}
            Filename: {file.filename}
            
            Extract:
            1. Key technical specifications
            2. Pricing information
            3. Timeline details
            4. Compliance statements
            5. Risk factors
            
            Provide as structured summary.
            """
            
            try:
                analysis_response = await llm.ainvoke(analysis_prompt)
                document["ai_extraction"] = {
                    "summary": analysis_response.content,
                    "extracted_at": int(datetime.now().timestamp())
                }
            except Exception as ai_error:
                print(f"Document AI analysis failed: {ai_error}")
                document["ai_extraction"] = {"error": "Analysis failed"}
        
        # Save document record to database
        db = get_db_connection()
        db.child("bid_documents").child(bid_id).child(document_id).set(document)
        
        # Update bid with document reference
        existing_documents = existing_bid.get("documents", [])
        existing_documents.append(document_id)
        await update_bid(bid_id, {"documents": existing_documents})
        
        return document
    except Exception as e:
        print(f"Error uploading bid document: {e}")
        raise e

async def get_bid_documents(bid_id: str) -> List[Dict]:
    """Get all documents for a bid."""
    try:
        db = get_db_connection()
        documents = db.child("bid_documents").child(bid_id).get()
        
        if documents.val():
            return [{"id": k, **v} for k, v in documents.val().items()]
        return []
    except Exception as e:
        print(f"Error getting bid documents for {bid_id}: {e}")
        return []
