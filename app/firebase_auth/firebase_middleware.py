from flask import request, jsonify
from functools import wraps
import logging
from firebase_admin import auth
from app.services.user_service import get_or_create_user_profile

logger = logging.getLogger(__name__)

def firebase_token_required(f):
    """Decorator to require Firebase ID token for routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        # Extract token from Authorization header
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split('Bearer ')[1]
        
        if not token:
            logger.warning(f"Missing Firebase token in request to {request.path}")
            return jsonify({
                'status': 'error',
                'message': 'Authentication token is missing'
            }), 401
        
        try:
            # Verify the Firebase ID token
            decoded_token = auth.verify_id_token(token)
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email')
            
            # Get or create user profile in Firestore
            user_profile = get_or_create_user_profile(firebase_uid, email)
            
            if not user_profile:
                logger.error(f"Failed to get user profile for Firebase UID: {firebase_uid}")
                return jsonify({
                    'status': 'error',
                    'message': 'User profile not found'
                }), 404
            
            # Add user info to request for use in route handlers
            request.user = {
                'firebase_uid': firebase_uid,
                'user_id': user_profile.get('user_id'),
                'email': email,
                'role': user_profile.get('role', 'user'),
                'name': user_profile.get('name')
            }
            
            logger.info(f"Authenticated Firebase user {firebase_uid} for {request.path}")
            return f(*args, **kwargs)
            
        except auth.ExpiredIdTokenError:
            logger.warning("Firebase token has expired")
            return jsonify({
                'status': 'error',
                'message': 'Token has expired'
            }), 401
        except auth.InvalidIdTokenError:
            logger.warning("Invalid Firebase token")
            return jsonify({
                'status': 'error',
                'message': 'Invalid token'
            }), 401
        except Exception as e:
            logger.error(f"Firebase token verification failed: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Authentication failed'
            }), 401
    
    return decorated

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @firebase_token_required
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'admin':
            logger.warning(f"Non-admin user {request.user.get('firebase_uid')} tried to access admin route {request.path}")
            return jsonify({
                'status': 'error',
                'message': 'Admin privileges required'
            }), 403
        
        logger.info(f"Admin access granted for user {request.user.get('firebase_uid')} to {request.path}")
        return f(*args, **kwargs)
    
    return decorated