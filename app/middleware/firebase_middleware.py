from functools import wraps
from flask import request, jsonify
from app.services.firebase_service import FirebaseAuthService

def firebase_auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'status': 'error', 'message': 'No token provided'}), 401
        
        try:
            # Extract token from Bearer token
            id_token = auth_header.split('Bearer ')[1]
            
            # Verify token
            auth_info = FirebaseAuthService.verify_token(id_token)
            
            if auth_info['status'] == 'error':
                return jsonify(auth_info), 401
            
            # Add user info to request
            request.user = auth_info
            
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': 'Invalid token'
            }), 401
            
    return decorated