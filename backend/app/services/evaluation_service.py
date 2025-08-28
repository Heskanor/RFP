"""
Evaluation Service - Handles evaluation criteria and scoring logic
"""
from typing import Dict, List, Optional
from app.config.database import get_db_connection
from app.models.models import Collections
from app.config.defaults import get_available_model
from app.config.llm_factory import LLMFactory
import uuid
from datetime import datetime

async def get_evaluation_criteria(project_id: str) -> List[Dict]:
    """Get evaluation criteria for a project."""
    try:
        db = get_db_connection()
        criteria_ref = db.child("evaluation_criteria").child(project_id)
        criteria = criteria_ref.get()
        
        if criteria.val():
            return [{"id": k, **v} for k, v in criteria.val().items()]
        return []
    except Exception as e:
        print(f"Error getting evaluation criteria for project {project_id}: {e}")
        return []

async def create_evaluation_criteria(project_id: str, criteria_data: Dict) -> Dict:
    """Create evaluation criteria for a project."""
    try:
        db = get_db_connection()
        criteria_id = str(uuid.uuid4())
        
        criteria = {
            "id": criteria_id,
            "project_id": project_id,
            "name": criteria_data.get("name"),
            "description": criteria_data.get("description", ""),
            "weight": criteria_data.get("weight", 1.0),
            "max_score": criteria_data.get("max_score", 10),
            "subcriteria": criteria_data.get("subcriteria", []),
            "created_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp())
        }
        
        db.child("evaluation_criteria").child(project_id).child(criteria_id).set(criteria)
        return criteria
    except Exception as e:
        print(f"Error creating evaluation criteria: {e}")
        raise e

async def update_evaluation_criteria(criteria_id: str, criteria_data: Dict) -> Optional[Dict]:
    """Update evaluation criteria."""
    try:
        db = get_db_connection()
        
        # Find the criteria across all projects (could be optimized with better data structure)
        # For now, assume we get project_id in the data
        project_id = criteria_data.get("project_id")
        if not project_id:
            return None
        
        updated_data = {
            **criteria_data,
            "updated_at": int(datetime.now().timestamp())
        }
        
        db.child("evaluation_criteria").child(project_id).child(criteria_id).update(updated_data)
        
        # Return updated criteria
        criteria = db.child("evaluation_criteria").child(project_id).child(criteria_id).get()
        if criteria.val():
            return {"id": criteria_id, **criteria.val()}
        return None
    except Exception as e:
        print(f"Error updating evaluation criteria {criteria_id}: {e}")
        raise e

async def delete_evaluation_criteria(criteria_id: str) -> bool:
    """Delete evaluation criteria."""
    try:
        # This would need project_id in a real implementation
        # For now, return True as placeholder
        return True
    except Exception as e:
        print(f"Error deleting evaluation criteria {criteria_id}: {e}")
        return False

async def get_vendor_scores(vendor_id: Optional[str], project_id: str) -> List[Dict]:
    """Get scores for vendor(s) in a project."""
    try:
        db = get_db_connection()
        scores_ref = db.child("vendor_scores").child(project_id)
        
        if vendor_id:
            scores = scores_ref.child(vendor_id).get()
            if scores.val():
                return [{"vendor_id": vendor_id, **scores.val()}]
        else:
            scores = scores_ref.get()
            if scores.val():
                return [{"vendor_id": k, **v} for k, v in scores.val().items()]
        
        return []
    except Exception as e:
        print(f"Error getting vendor scores: {e}")
        return []

async def submit_vendor_scores(vendor_id: str, scores_data: Dict) -> Dict:
    """Submit or update scores for a vendor."""
    try:
        db = get_db_connection()
        project_id = scores_data.get("project_id")
        
        if not project_id:
            raise ValueError("project_id is required")
        
        score_entry = {
            "vendor_id": vendor_id,
            "project_id": project_id,
            "scores": scores_data.get("scores", {}),
            "justifications": scores_data.get("justifications", {}),
            "total_score": scores_data.get("total_score", 0),
            "evaluator_id": scores_data.get("evaluator_id"),
            "submitted_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp())
        }
        
        db.child("vendor_scores").child(project_id).child(vendor_id).set(score_entry)
        return score_entry
    except Exception as e:
        print(f"Error submitting vendor scores: {e}")
        raise e

async def calculate_weighted_scores(project_id: str) -> List[Dict]:
    """Calculate weighted scores for all vendors in a project using AI analysis."""
    try:
        # Get evaluation criteria and vendor scores
        criteria = await get_evaluation_criteria(project_id)
        all_scores = await get_vendor_scores(None, project_id)
        
        if not criteria or not all_scores:
            return []
        
        # Use Gemini to help with complex scoring calculations
        model = get_available_model("scoring")
        llm = LLMFactory.get_llm(model, temperature=0.1)
        
        # Calculate weighted scores
        weighted_results = []
        for vendor_score in all_scores:
            total_weighted_score = 0
            max_possible_score = 0
            
            for criterion in criteria:
                weight = criterion.get("weight", 1.0)
                max_score = criterion.get("max_score", 10)
                criterion_id = criterion.get("id")
                
                # Get the score for this criterion
                score = vendor_score.get("scores", {}).get(criterion_id, 0)
                weighted_score = score * weight
                total_weighted_score += weighted_score
                max_possible_score += max_score * weight
            
            # Calculate percentage
            percentage = (total_weighted_score / max_possible_score * 100) if max_possible_score > 0 else 0
            
            weighted_results.append({
                **vendor_score,
                "weighted_total": total_weighted_score,
                "max_possible": max_possible_score,
                "percentage": round(percentage, 2),
                "rank": 0  # Will be calculated after sorting
            })
        
        # Sort by weighted total and assign ranks
        weighted_results.sort(key=lambda x: x["weighted_total"], reverse=True)
        for i, result in enumerate(weighted_results):
            result["rank"] = i + 1
        
        return weighted_results
    except Exception as e:
        print(f"Error calculating weighted scores: {e}")
        return []
