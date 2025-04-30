from flask import Blueprint, request, jsonify
import logging
from app.validators import (
    validate_json_request, 
    handle_api_exception,
    validate_string,
    validate_email,
    validate_password
)
from app.services.auth_service import (
    create_user,
    login_user,
    get_user_profile,
    update_user_profile,
    change_password
)

auth_routes = Blueprint('auth_routes', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@auth_routes.route('/api/auth/register', methods=['POST'])
@validate_json_request(required_fields=['email', 'password', 'name'])
@handle_api_exception
def register():
    """Register a new user"""
    data = request.json
    logger.info(f"User registration request received for: {data.get('email')}")
    
    # Validate inputs
    email_error = validate_email(data.get('email'), company_domain='lokatani.com')
    if email_error:
        logger.warning(f"Email validation failed: {email_error}")
        return jsonify({"status": "error", "message": email_error}), 400
    
    password_error = validate_password(data.get('password'))
    if password_error:
        logger.warning(f"Password validation failed: {data.get('email')}")
        return jsonify({"status": "error", "message": password_error}), 400
    
    name_error = validate_string(data.get('name'), 'Name')
    if name_error:
        logger.warning(f"Name validation failed: {name_error}")
        return jsonify({"status": "error", "message": name_error}), 400
    
    # Process registration
    result = create_user(
        email=data.get('email'),
        password=data.get('password'),
        name=data.get('name'),
        role=data.get('role', 'user')  # Default role is 'user'
    )
    
    if result.get('status') == 'error':
        logger.warning(f"Registration failed: {result.get('message')}")
        return jsonify(result), 400
    
    logger.info(f"User registered successfully: {result.get('user_id')}")
    return jsonify(result), 201

@auth_routes.route('/api/auth/login', methods=['POST'])
@validate_json_request(required_fields=['email', 'password'])
@handle_api_exception
def login():
    """Login existing user"""
    data = request.json
    logger.info(f"Login attempt for: {data.get('email')}")
    
    # Process login
    result = login_user(
        email=data.get('email'),
        password=data.get('password')
    )
    
    if result.get('status') == 'error':
        logger.warning(f"Login failed for {data.get('email')}: {result.get('message')}")
        return jsonify(result), 401
    
    logger.info(f"User logged in successfully: {result.get('user_id')}")
    return jsonify(result), 200

@auth_routes.route('/api/auth/profile/<user_id>', methods=['GET'])
@handle_api_exception
def get_profile(user_id):
    """Get user profile information"""
    logger.info(f"Profile request for user: {user_id}")
    
    # Validate user_id
    if not user_id:
        logger.warning("Missing user_id in profile request")
        return jsonify({"status": "error", "message": "User ID is required"}), 400
    
    # Fetch profile
    result = get_user_profile(user_id)
    
    if result.get('status') == 'error':
        logger.warning(f"Profile request failed: {result.get('message')}")
        return jsonify(result), 404
    
    logger.info(f"Profile retrieved for user: {user_id}")
    return jsonify(result), 200

@auth_routes.route('/api/auth/profile', methods=['PUT'])
@validate_json_request(required_fields=['user_id'])
@handle_api_exception
def update_profile():
    """Update user profile information"""
    data = request.json
    user_id = data.get('user_id')
    logger.info(f"Profile update request for user: {user_id}")
    
    # Update profile
    result = update_user_profile(user_id, data)
    
    if result.get('status') == 'error':
        logger.warning(f"Profile update failed: {result.get('message')}")
        return jsonify(result), 404
    
    logger.info(f"Profile updated for user: {user_id}")
    return jsonify(result), 200

@auth_routes.route('/api/auth/password', methods=['PUT'])
@validate_json_request(required_fields=['user_id', 'current_password', 'new_password'])
@handle_api_exception
def update_password():
    """Change user password"""
    data = request.json
    user_id = data.get('user_id')
    logger.info(f"Password change request for user: {user_id}")
    
    # Validate new password
    password_error = validate_password(data.get('new_password'))
    if password_error:
        logger.warning(f"New password validation failed for user: {user_id}")
        return jsonify({"status": "error", "message": password_error}), 400
    
    # Change password
    result = change_password(
        user_id=user_id,
        current_password=data.get('current_password'),
        new_password=data.get('new_password')
    )
    
    if result.get('status') == 'error':
        logger.warning(f"Password change failed: {result.get('message')}")
        return jsonify(result), 400
    
    logger.info(f"Password changed successfully for user: {user_id}")
    return jsonify(result), 200