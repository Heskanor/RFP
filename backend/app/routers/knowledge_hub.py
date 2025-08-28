from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Literal, Union
from app.config.firebase import firebase_manager
from app.services.knowledgehub.knowledge_hub_service import (
   create_knowledge_items, 
   get_knowledge_items, 
   get_knowledge_item, 
   update_knowledge_item, 
   delete_knowledge_items, 
   get_knowledge_hub_stats, 
   get_knowledge_items_by_text_filter)
from app.models.models import KnowledgeItem, CuratedQAContent
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/knowledge-hub", tags=["Knowledge Hub"])

COLLECTION_NAME = "knowledge_items"


# ---------- CREATE ----------
@router.post("")
async def create_knowledge_items_route(items: List[KnowledgeItem]):
   print(f"Creating knowledge items: {items}")
   result = await create_knowledge_items(items)

   if "error" in result:
      raise HTTPException(status_code=500, detail=result["message"])

   return result


# ---------- GET ALL (with filters) ----------
@router.get("", response_model=List[KnowledgeItem])
async def get_knowledge_items_route(
    user_id: str,
    type: Optional[Literal["uploaded_documents", "curated_qa", "web_page", "custom_connector"]] = None,
    subtype: Optional[str] = None,
    label_id: Optional[str] = None,
    expand_labels: Optional[bool] = False
):
   result = await get_knowledge_items(user_id=user_id, type=type, subtype=subtype, label_id=label_id, expand_labels=expand_labels)
   if "error" in result:
      raise HTTPException(status_code=500, detail=result["message"])
   # print(len(result.get("data", [])))
   return result.get("data", [])

#-------------------- GET ALL By text filter --------------------
@router.get("/search")
async def get_knowledge_items_by_text_filter_route(
    user_id: str,
    text: str,
   #  type: Optional[Literal["uploaded_documents", "curated_qa", "web_page", "custom_connector"]] = None,  
   #  subtype: Optional[str] = None,
   #  label_id: Optional[str] = None,
   #  expand_labels: Optional[bool] = False
):
   print(f"Searching for knowledge items with text: {text}")
   result = await get_knowledge_items_by_text_filter(user_id=user_id, text=text)

   if "error" in result:
      raise HTTPException(status_code=500, detail=result["message"])

   return result.get("data", []) 



# ---------- GET BY ID ----------
@router.get("/{item_id}", response_model=KnowledgeItem)
async def get_knowledge_item_route(item_id: str):
   result = await get_knowledge_item(item_id)

   if "error" in result:
      raise HTTPException(status_code=500, detail=result["message"])

   return result.get("data", {})

#----------- GET Stats ----------
@router.get("/{user_id}/stats")
async def get_knowledge_hub_stats_route(user_id: str):
   result = await get_knowledge_hub_stats(user_id)

   if "error" in result:
      raise HTTPException(status_code=500, detail=result["message"])
   
   return result.get("data", {})
# ---------- UPDATE ----------
@router.put("/{item_id}")
async def update_knowledge_item_route(item_id: str, updated_item: dict):
   result = await update_knowledge_item(item_id, updated_item)

   if "error" in result:
      raise HTTPException(status_code=500, detail=result["message"])

   return result.get("data", {})



# ---------- DELETE ----------
@router.delete("")
async def delete_knowledge_items_route(
    item_ids: Optional[List[str]] = Body(default=[], description="List of item ids to delete"),
    content_ids: Optional[List[str]] = Body(default=[], description="List of content ids to delete")):

   print(f"Deleting knowledge items with item_ids: {item_ids} and content_ids: {content_ids}")
   result = await delete_knowledge_items(item_ids=item_ids, content_ids=content_ids)

   if "error" in result:
      raise HTTPException(status_code=500, detail=result["message"])

   return result.get("data", {})

