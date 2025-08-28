"""
FastAPI main application for RFP Buyer - Document-based RFP evaluation platform
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging
import os

from fastapi.responses import JSONResponse

# Original routers (temporarily disabled for testing)
# from app.routers.project import router as project_router
# from app.routers.dossier import router as dossier_router
# from app.routers.file import router as file_router
# from app.routers.search import router as search_router
# from app.routers.ticket import router as ticket_router
# from app.routers.thread import router as thread_router
# from app.routers.user import router as user_router
# from app.routers.labels import router as labels_router
# from app.routers.knowledge_hub import router as knowledge_hub_router
# from app.routers.web_pages import router as web_pages_router
# from app.routers.websockets import router as websocket_router
# from app.routers.vendor import router as vendor_router
# from app.routers.evaluation import router as evaluation_router
# from app.routers.bid import router as bid_router 

# New clean structured routers
from app.routers.projects import router as projects_router
from app.routers.rfps import router as rfps_router
from app.routers.bids import router as bids_router
from app.routers.evaluations import router as evaluations_router

# New architecture imports
from app.auth import initialize_firebase
from app.db import initialize_database, close_database, health_check

import dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv.load_dotenv()


app = FastAPI(
    title="RFP Buyer API",
    description="API for RFP Buyer - comprehensive RFP management for buyers",
    version="1.0.0",
)

CORS_ORIGINS = [
    "https://magic-rfp-app-dev.web.app",
    "ws://magic-rfp-app-dev.web.app",
    "https://rfp.cube5.ai",
    "ws://rfp.cube5.ai",
    "http://localhost:5173",  # Vite dev server
    "ws://localhost:5173",   # Vite dev server websockets
    # "ws://localhost:8000"
]

CORS_ORIGINS_REGEX = ".*://localhost:.*"
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# fetch_prompts_on_startup()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting RFP Buyer API...")
    
    try:
        # Initialize Firebase Auth
        initialize_firebase()
        logger.info("✓ Firebase Auth initialized")
        
        # Initialize database connections  
        await initialize_database()
        logger.info("✓ Database connections initialized")
        
        logger.info("🚀 RFP Buyer API started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        # Don't fail startup - services will initialize on first use
        logger.warning("Services will initialize on first use")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on shutdown"""
    logger.info("Shutting down RFP Buyer API...")
    
    try:
        # Cleanup database connections
        await close_database()
        logger.info("✓ Database connections closed")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")
    
    logger.info("👋 Shutdown complete")


@app.get("/")
def root():
    """API root endpoint"""
    return {
        "message": "Welcome to the RFP Buyer API",
        "version": "1.0.0",
        "docs": "/docs",
        "architecture": {
            "frontend": "React 19 + React Router 7 + TypeScript + Tailwind + shadcn/ui",
            "backend": "Python 3.11+ + FastAPI",
            "auth": "Firebase Auth (JWT verification)",
            "database": "Supabase Postgres + Storage",
            "ai": "Gemini via google-generativeai SDK",
            "vector_search": "Pluggable (pgvector default, Pinecone optional)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if services are available
        services_status = {}
        
        # Check AI Orchestrator
        try:
            ai_orchestrator = get_ai_orchestrator()
            services_status["ai_orchestrator"] = {
                "status": "healthy",
                "provider": ai_orchestrator.provider
            }
        except Exception as e:
            services_status["ai_orchestrator"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check Vector Adapter
        try:
            vector_adapter = get_vector_adapter()
            backend_info = vector_adapter.get_backend_info()
            services_status["vector_search"] = {
                "status": "healthy",
                **backend_info
            }
        except Exception as e:
            services_status["vector_search"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check Database
        try:
            db_healthy = await health_check()
            services_status["database"] = {
                "status": "healthy" if db_healthy else "error",
                "message": "Connected" if db_healthy else "Connection failed"
            }
        except Exception as e:
            services_status["database"] = {
                "status": "error", 
                "error": str(e)
            }
        
        return {
            "status": "healthy",
            "timestamp": os.environ.get("TIMESTAMP", "unknown"),
            "services": services_status
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Core routers from magic-rfp-api (temporarily disabled for testing)
# app.include_router(user_router, prefix="/api/v1")
# app.include_router(project_router, prefix="/api/v1")
# app.include_router(dossier_router, prefix="/api/v1")
# app.include_router(file_router, prefix="/api/v1")
# app.include_router(ticket_router, prefix="/api/v1")
# app.include_router(thread_router, prefix="/api/v1")
# app.include_router(knowledge_hub_router, prefix="/api/v1")
# app.include_router(web_pages_router, prefix="/api/v1")
# app.include_router(labels_router, prefix="/api/v1")
# app.include_router(websocket_router, prefix="/api/v1")
# app.include_router(search_router, prefix="/api/v1")

# RFP Buyer specific routers (original - temporarily disabled)
# app.include_router(vendor_router, prefix="/api/v1")
# app.include_router(evaluation_router, prefix="/api/v1")
# app.include_router(bid_router, prefix="/api/v1")

# New structured RFP routers
app.include_router(projects_router, prefix="/api/v1", tags=["projects"])
app.include_router(rfps_router, prefix="/api/v1", tags=["rfps"])
app.include_router(bids_router, prefix="/api/v1", tags=["bids"])
app.include_router(evaluations_router, prefix="/api/v1", tags=["evaluations"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
