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
from app.jwt.jwt_handler import generate_token, refresh_access_token
from app.jwt.jwt_middleware import token_required

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
    email_error = validate_email(data.get('email'), company_domain='lokatani.id')
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
    
    # Generate tokens for immediate login after registration
    try:
        user_id = result.get('user_id')
        email = result.get('email')
        role = result.get('role')
        
        access_token = generate_token(user_id, email, role, 'access')
        refresh_token = generate_token(user_id, email, role, 'refresh')
        
        # Add tokens to result
        result['access_token'] = access_token
        result['refresh_token'] = refresh_token
        
        logger.info(f"User registered successfully with tokens: {access_token}. Result: {result}")
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Token generation failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Registration error"
        }), 500

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
    
    # Generate JWT tokens
    try:
        user_id = result.get('user_id')
        email = result.get('email')
        role = result.get('role')
        
        access_token = generate_token(user_id, email, role, 'access')
        refresh_token = generate_token(user_id, email, role, 'refresh')
        
        # Add tokens to result
        result['access_token'] = access_token
        result['refresh_token'] = refresh_token
        
        logger.info(f"User logged in successfully with tokens: {user_id}. Result: {result}")
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Token generation failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Authentication error"
        }), 500

@auth_routes.route('/api/auth/refresh', methods=['POST'])
@validate_json_request(required_fields=['refresh_token'])
@handle_api_exception
def refresh():
    """Refresh access token using refresh token"""
    data = request.json
    refresh_token = data.get('refresh_token')
    
    logger.info("Token refresh request received")
    
    # Call the modified refresh_access_token function
    tokens = refresh_access_token(refresh_token)
    
    if not tokens:
        logger.warning("Token refresh failed: invalid or expired refresh token")
        return jsonify({
            "status": "error",
            "message": "Invalid or expired refresh token"
        }), 401
    
    logger.info("Access token refreshed successfully")
    return jsonify({
        "status": "success",
        **tokens,
        "message": "Token refreshed successfully"
    }), 200

@auth_routes.route('/api/auth/profile/<user_id>', methods=['GET'])
@token_required
@handle_api_exception
def get_profile(user_id):
    """Get user profile information"""
    logger.info(f"Profile request for user: {user_id}")
    
    # Validate user_id
    if not user_id:
        logger.warning("Missing user_id in profile request")
        return jsonify({"status": "error", "message": "User ID is required"}), 400
    
    # Verify the user is accessing their own profile, unless they're an admin
    if request.user.get('user_id') != user_id and request.user.get('role') != 'admin':
        logger.warning(f"User {request.user.get('user_id')} attempted to access profile of {user_id}")
        return jsonify({
            "status": "error",
            "message": "Unauthorized access to profile"
        }), 403
    
    # Fetch profile
    result = get_user_profile(user_id)
    
    if result.get('status') == 'error':
        logger.warning(f"Profile request failed: {result.get('message')}")
        return jsonify(result), 404
    
    logger.info(f"Profile retrieved for user: {user_id}")
    return jsonify(result), 200

@auth_routes.route('/api/auth/profile', methods=['PUT'])
@token_required
@validate_json_request(required_fields=['user_id'])
@handle_api_exception
def update_profile():
    """Update user profile information"""
    data = request.json
    user_id = data.get('user_id')
    logger.info(f"Profile update request for user: {user_id}")
    
    # Verify the user is updating their own profile, unless they're an admin
    if request.user.get('user_id') != user_id and request.user.get('role') != 'admin':
        logger.warning(f"User {request.user.get('user_id')} attempted to update profile of {user_id}")
        return jsonify({
            "status": "error",
            "message": "Unauthorized profile update"
        }), 403
    
    # Update profile
    result = update_user_profile(user_id, data)
    
    if result.get('status') == 'error':
        logger.warning(f"Profile update failed: {result.get('message')}")
        return jsonify(result), 404
    
    logger.info(f"Profile updated for user: {user_id}")
    return jsonify(result), 200

@auth_routes.route('/api/auth/password', methods=['PUT'])
@token_required
@validate_json_request(required_fields=['user_id', 'current_password', 'new_password'])
@handle_api_exception
def update_password():
    """Change user password"""
    data = request.json
    user_id = data.get('user_id')
    logger.info(f"Password change request for user: {user_id}")
    
    # Verify the user is changing their own password
    if request.user.get('user_id') != user_id:
        logger.warning(f"User {request.user.get('user_id')} attempted to change password of {user_id}")
        return jsonify({
            "status": "error",
            "message": "Unauthorized password change"
        }), 403
    
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