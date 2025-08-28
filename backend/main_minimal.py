"""
Minimal RFP Buyer API - Gemini Only
Start here to test Gemini integration without Firebase dependencies
"""
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import dotenv
import os

# Load environment variables
dotenv.load_dotenv()

app = FastAPI(
    title="RFP Buyer API (Gemini Only)",
    description="Minimal API for testing Gemini AI integration",
    version="1.0.0-minimal",
)

# CORS middleware
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "ws://localhost:5173",   # Vite dev server websockets
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=".*://localhost:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to RFP Buyer API (Gemini Only)",
        "version": "1.0.0-minimal",
        "docs": "/docs",
        "status": "✅ Ready for Gemini testing!"
    }

# Test Gemini endpoint
@app.post("/test/gemini")
async def test_gemini(prompt: str = "Hello, how are you?"):
    """Test Gemini API integration"""
    try:
        from app.config.defaults import get_available_model
        from app.config.llm_factory import LLMFactory
        
        # Check if Gemini is available
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            return {
                "error": "GOOGLE_API_KEY not found in environment",
                "setup_needed": "Add your Gemini API key to api/.env"
            }
        
        # Get Gemini model
        model = get_available_model("chat")
        llm = LLMFactory.get_llm(model, temperature=0.1)
        
        # Test Gemini
        response = await llm.ainvoke(prompt)
        
        return {
            "model": model.value,
            "prompt": prompt,
            "response": response.content,
            "status": "✅ Gemini working!"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "model_attempted": "gemini-2.5-flash",
            "troubleshooting": "Check your GOOGLE_API_KEY in api/.env"
        }

# Simple vendor analysis endpoint (no database)
@app.post("/analyze/vendor")
async def analyze_vendor(vendor_data: dict = Body(...)):
    """Analyze a vendor using Gemini AI"""
    try:
        # Extract data from JSON body
        name = vendor_data.get("name", "Unknown Vendor")
        description = vendor_data.get("description", "No description provided")
        industry = vendor_data.get("industry", "Unknown")
        
        # Use direct Gemini API like the test endpoint
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        analysis_prompt = f"""
        Analyze this vendor for an RFP evaluation:
        
        Name: {name}
        Industry: {industry}
        Description: {description}
        
        Provide analysis on:
        1. Strengths and competitive advantages
        2. Potential weaknesses or risks
        3. Market position assessment
        4. Recommended evaluation criteria
        5. Overall suitability score (1-10)
        
        Keep the response concise and practical.
        """
        
        response = model.generate_content(analysis_prompt)
        
        return {
            "vendor": {
                "name": name,
                "industry": industry,
                "description": description
            },
            "analysis": response.text,
            "model_used": "gemini-2.5-flash",
            "status": "✅ Analysis complete"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "vendor": {"name": name, "industry": industry},
            "status": "❌ Analysis failed"
        }

# Simple bid analysis endpoint (no database)
@app.post("/analyze/bid")
async def analyze_bid(bid_data: dict = Body(...)):
    """Analyze a bid using Gemini AI"""
    try:
        # Extract data from JSON body
        title = bid_data.get("title", "Untitled Bid")
        summary = bid_data.get("summary", "No summary provided")
        cost = bid_data.get("cost", 0.0)
        currency = bid_data.get("currency", "USD")
        
        # Use direct Gemini API like the test endpoint
        import google.generativeai as genai
        
        # Configure Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        analysis_prompt = f"""
        Analyze this RFP bid submission:
        
        Title: {title}
        Summary: {summary}
        Cost: {cost} {currency}
        
        Provide analysis on:
        1. Strengths of the proposal
        2. Potential weaknesses or gaps
        3. Cost competitiveness assessment
        4. Risk factors to consider
        5. Overall recommendation (Accept/Review/Reject)
        6. Confidence score (1-10)
        
        Keep the response concise and practical.
        """
        
        response = model.generate_content(analysis_prompt)
        
        return {
            "bid": {
                "title": title,
                "summary": summary,
                "cost": f"{cost} {currency}"
            },
            "analysis": response.text,
            "model_used": "gemini-2.5-flash",
            "status": "✅ Bid analysis complete"
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "bid": {"title": title, "cost": f"{cost} {currency}"},
            "status": "❌ Analysis failed"
        }

# Document Processing Endpoints for RFP Evaluation
@app.post("/api/v1/projects/{project_id}/rfp/upload")
async def upload_rfp(project_id: str, rfp_data: dict = Body(...)):
    """Upload RFP document and extract criteria using AI"""
    try:
        # Extract RFP content (text, file, or URL)
        rfp_text = rfp_data.get("text", "")
        rfp_file = rfp_data.get("file", None)
        rfp_url = rfp_data.get("url", None)
        
        # Use direct Gemini API for criteria extraction
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        extraction_prompt = f"""
        Extract evaluation criteria from this RFP document:
        
        RFP Content: {rfp_text}
        
        Identify and extract:
        1. Main evaluation criteria categories
        2. Sub-criteria for each category
        3. Suggested scoring methodology
        4. Required vendor qualifications
        5. Technical requirements
        
        Format as JSON with structure:
        {{
          "criteria": [
            {{
              "id": "experience_capabilities",
              "title": "Experience and Capabilities",
              "weight": 20,
              "sub_criteria": [
                {{"id": "sub1", "title": "Years in business", "description": "..."}}
              ]
            }}
          ]
        }}
        """
        
        response = model.generate_content(extraction_prompt)
        
        return {
            "project_id": project_id,
            "rfp_content": rfp_text[:200] + "..." if len(rfp_text) > 200 else rfp_text,
            "extracted_criteria": response.text,
            "status": "✅ RFP processed and criteria extracted"
        }
        
    except Exception as e:
        return {"error": f"RFP processing failed: {str(e)}"}

@app.post("/api/v1/projects/{project_id}/bids/upload")
async def upload_bid(project_id: str, bid_data: dict = Body(...)):
    """Upload bid document and extract vendor profile + responses"""
    try:
        # Extract bid content
        bid_text = bid_data.get("text", "")
        vendor_name = bid_data.get("vendor_name", "Unknown Vendor")
        
        # Use direct Gemini API for bid analysis
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        analysis_prompt = f"""
        Analyze this bid document and extract vendor information:
        
        Bid Content: {bid_text}
        
        Extract and analyze:
        1. Company name and background
        2. Experience and capabilities
        3. Technical approach and methodology  
        4. Compliance and regulatory alignment
        5. Cost information and value proposition
        6. Innovation and technology offerings
        
        For each criterion, provide:
        - Score (0-100)
        - Justification based on document content
        - Key strengths and weaknesses
        
        Format as JSON with vendor profile and criterion scores.
        """
        
        response = model.generate_content(analysis_prompt)
        
        return {
            "project_id": project_id,
            "vendor_name": vendor_name,
            "bid_content": bid_text[:200] + "..." if len(bid_text) > 200 else bid_text,
            "vendor_profile": response.text,
            "status": "✅ Bid processed and vendor profile generated"
        }
        
    except Exception as e:
        return {"error": f"Bid processing failed: {str(e)}"}

# Data Retrieval Endpoints  
@app.get("/api/v1/projects/{project_id}/vendors")
async def get_project_vendors(project_id: str):
    """Get all vendor profiles for a project"""
    # Mock data for now - will be replaced with real database
    return {
        "project_id": project_id,
        "vendors": [
            {"name": "TechCorp Solutions", "profile": "AI-generated profile..."},
            {"name": "Innovation Partners", "profile": "AI-generated profile..."},
            {"name": "Digital Dynamics", "profile": "AI-generated profile..."}
        ]
    }

@app.get("/api/v1/projects/{project_id}/criteria")  
async def get_project_criteria(project_id: str):
    """Get extracted criteria for a project"""
    # Mock data for now - will be replaced with real database
    return {
        "project_id": project_id,
        "criteria": [
            {
                "id": "experience_capabilities",
                "title": "Experience and Capabilities", 
                "weight": 20,
                "sub_criteria": []
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


