"""
Firebase Auth JWT Verification Middleware
"""
import os
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials
import json

logger = logging.getLogger(__name__)

# Global Firebase app instance
_firebase_app = None

def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK"""
    global _firebase_app
    
    if _firebase_app is not None:
        return  # Already initialized
    
    try:
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        if not project_id:
            raise ValueError("FIREBASE_PROJECT_ID environment variable is required")
        
        # Initialize with default credentials or service account
        firebase_config_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        
        if firebase_config_json:
            # Use service account JSON if provided
            try:
                service_account_info = json.loads(firebase_config_json)
                cred = credentials.Certificate(service_account_info)
            except json.JSONDecodeError:
                # Assume it's a file path
                cred = credentials.Certificate(firebase_config_json)
        else:
            # Use default credentials (for deployed environments)
            cred = credentials.ApplicationDefault()
        
        _firebase_app = firebase_admin.initialize_app(cred, {
            'projectId': project_id,
        })
        
        logger.info(f"Firebase Admin SDK initialized for project: {project_id}")
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise


class FirebaseAuthBearer(HTTPBearer):
    """Custom HTTPBearer for Firebase JWT verification"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if credentials:
            if not credentials.scheme == "Bearer":
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication scheme",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                return None
            
            # Verify the JWT token
            user_info = await self.verify_jwt(credentials.credentials)
            if not user_info:
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                return None
            
            # Add user info to request state
            request.state.user = user_info
            return credentials
        
        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None
    
    async def verify_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase JWT token"""
        try:
            # Ensure Firebase is initialized
            if _firebase_app is None:
                initialize_firebase()
            
            # Verify the token
            decoded_token = auth.verify_id_token(token)
            
            # Extract user information
            user_info = {
                "uid": decoded_token.get("uid"),
                "email": decoded_token.get("email"),
                "email_verified": decoded_token.get("email_verified", False),
                "name": decoded_token.get("name"),
                "picture": decoded_token.get("picture"),
                "firebase_claims": decoded_token
            }
            
            logger.debug(f"Successfully verified token for user: {user_info.get('email')}")
            return user_info
            
        except auth.ExpiredIdTokenError:
            logger.warning("Firebase token has expired")
            return None
        except auth.RevokedIdTokenError:
            logger.warning("Firebase token has been revoked")
            return None
        except auth.InvalidIdTokenError as e:
            logger.warning(f"Invalid Firebase token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying Firebase token: {e}")
            return None


# Global auth bearer instance
firebase_auth = FirebaseAuthBearer()


# Dependency functions for FastAPI routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(firebase_auth)) -> Dict[str, Any]:
    """Get current authenticated user from Firebase JWT"""
    # The user info should already be set in request.state by FirebaseAuthBearer
    # This is a fallback that re-verifies the token
    user_info = await firebase_auth.verify_jwt(credentials.credentials)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_info


async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, None otherwise"""
    return getattr(request.state, 'user', None)


async def get_user_uid(user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """Get the Firebase UID of the current user"""
    return user["uid"]


async def get_user_email(user: Dict[str, Any] = Depends(get_current_user)) -> str:
    """Get the email of the current user"""
    email = user.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email not available"
        )
    return email


def require_email_verified(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require that the user's email is verified"""
    if not user.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return user


# Admin role checking (if using custom claims)
async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin role (based on custom claims)"""
    firebase_claims = user.get("firebase_claims", {})
    if not firebase_claims.get("admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user


# Utility function to extract user from request (for use in websockets, etc.)
def get_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Extract user info from request state (set by middleware)"""
    return getattr(request.state, 'user', None)


# Context manager for testing without authentication
class MockAuth:
    """Mock authentication for testing"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.user_data = user_data
    
    async def __call__(self, request: Request) -> Dict[str, Any]:
        request.state.user = self.user_data
        return self.user_data


def create_mock_user(
    uid: str = "test_user_123",
    email: str = "test@example.com",
    email_verified: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Create mock user data for testing"""
    return {
        "uid": uid,
        "email": email,
        "email_verified": email_verified,
        "name": kwargs.get("name", "Test User"),
        "picture": kwargs.get("picture"),
        "firebase_claims": {
            "uid": uid,
            "email": email,
            "email_verified": email_verified,
            **kwargs
        }
    }


# Initialize Firebase on module import
try:
    initialize_firebase()
except Exception as e:
    logger.warning(f"Firebase initialization failed during import: {e}")
    logger.info("Firebase will be initialized on first use")

