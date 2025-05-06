import jwt
import os
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-should-be-in-env')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour
JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800))  # 7 days

def generate_token(user_id, email, role, token_type='access'):
    """Generate a JWT token."""
    try:
        payload = {
            'sub': user_id,
            'email': email,
            'role': role,
            'iat': datetime.utcnow(),
            'type': token_type
        }
        
        # Set expiration time based on token type
        if token_type == 'access':
            payload['exp'] = datetime.utcnow() + timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES)
        elif token_type == 'refresh':
            payload['exp'] = datetime.utcnow() + timedelta(seconds=JWT_REFRESH_TOKEN_EXPIRES)
        
        # Generate token
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug(f"Generated {token_type} token for user {user_id}")
        
        return token
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise

def verify_token(token):
    """Verify a JWT token and return the decoded payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        logger.debug(f"Verified token for user {payload.get('sub')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None

def refresh_access_token(refresh_token):
    """Generate a new access token using a refresh token."""
    try:
        payload = verify_token(refresh_token)
        
        if payload is None:
            logger.warning("Invalid refresh token")
            return None
            
        if payload.get('type') != 'refresh':
            logger.warning("Token is not a refresh token")
            return None
            
        # Create new access token
        access_token = generate_token(
            payload['sub'], 
            payload['email'], 
            payload['role'], 
            'access'
        )
        
        logger.info(f"Refreshed access token for user {payload['sub']}")
        return access_token
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return None