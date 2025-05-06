from flask import request, jsonify
from functools import wraps
import logging
from app.jwt.jwt_handler import verify_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def token_required(f):
    """Decorator to require JWT token for routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        # Extract token from Authorization header
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
        
        if not token:
            logger.warning(f"Missing token in request to {request.path}")
            return jsonify({
                'status': 'error',
                'message': 'Authentication token is missing'
            }), 401
        
        # Verify the token
        payload = verify_token(token)
        if not payload:
            logger.warning(f"Invalid token in request to {request.path}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid or expired token'
            }), 401
        
        # Add user info to request for use in route handlers
        request.user = {
            'user_id': payload['sub'],
            'email': payload['email'],
            'role': payload['role']
        }
        
        logger.info(f"Authenticated request for user {payload['sub']} to {request.path}")
        return f(*args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator to require admin role in JWT token"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'admin':
            logger.warning(f"Non-admin user {request.user.get('user_id')} tried to access admin route {request.path}")
            return jsonify({
                'status': 'error',
                'message': 'Admin privileges required'
            }), 403
        
        logger.info(f"Admin access granted for user {request.user.get('user_id')} to {request.path}")
        return f(*args, **kwargs)
    
    return decorated