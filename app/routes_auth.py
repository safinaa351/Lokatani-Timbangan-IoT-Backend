from flask import Blueprint, request, jsonify
import logging
from app.validators import (
    validate_json_request, 
    handle_api_exception,
    validate_string
)
from app.services.user_service import (
    get_user_profile,
    update_user_profile,
    set_user_role
)
from app.firebase_auth.firebase_middleware import firebase_token_required, admin_required

auth_routes = Blueprint('auth_routes', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@auth_routes.route('/api/auth/profile/<user_id>', methods=['GET'])
@firebase_token_required
@handle_api_exception
def get_profile(user_id):
    """Get user profile information"""
    logger.info(f"Profile request for user: {user_id}")
    
    # Validate user_id
    if not user_id:
        logger.warning("Missing user_id in profile request")
        return jsonify({"status": "error", "message": "User ID is required"}), 400
    
    # Get the authenticated user's ID from the token
    authenticated_user_id = request.user.get('firebase_uid')
    if not authenticated_user_id:
         logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
         return jsonify({
             "status": "error",
             "message": "Authentication failed or user ID not available"
         }), 500

    # Verify the authenticated user is accessing their own profile, unless they're an admin
    if authenticated_user_id != user_id and request.user.get('role') != 'admin':
        logger.warning(f"User {authenticated_user_id} attempted to access profile of {user_id}")
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
@firebase_token_required
@handle_api_exception
def update_profile():
    data = request.json or {}
    logger.info(f"Authenticated user profile update request received. Data: {data}")

    # Get the authenticated user's ID from the token
    # This is the user whose profile will be updated
    authenticated_user_id = request.user.get('firebase_uid')
    if not authenticated_user_id:
         logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
         return jsonify({
             "status": "error",
             "message": "Authentication failed or user ID not available"
         }), 500

    # The target user ID is ALWAYS the authenticated user's ID for this endpoint.
    target_user_id = authenticated_user_id

    # Log if a user_id was included in the body, as it's not used here
    if 'user_id' in data:
         logger.warning(f"User {authenticated_user_id} included 'user_id' in profile update body ({data['user_id']}). This field is ignored as this endpoint only updates the authenticated user's profile.")
         del data['user_id'] # Remove it to be safe and keep data clean

    # Check if there's any actual data to update
    if not data:
        logger.warning(f"Profile update request for user {target_user_id} has empty body.")
        return jsonify({
            "status": "error",
            "message": "Request body is empty or contains no updatable fields"
        }), 400


    # Update profile using the authenticated user's ID and the update data
    # The service function `update_user_profile(target_user_id, update_data)` must use `target_user_id`
    logger.info(f"Updating profile for user ID: {target_user_id}")
    result = update_user_profile(target_user_id, data)

    if result and result.get('status') == 'error':
        if result.get('message') == 'Profile not found':
             logger.error(f"Authenticated user's profile not found during update for user {target_user_id}.")
             return jsonify({"status": "error", "message": "Your user profile was not found. Please contact support."}), 404
        # Handle other potential errors from the service (e.g., validation in service)
        logger.error(f"Profile update failed for user {target_user_id}: {result.get('message', 'Unknown error')}")
        return jsonify(result), 500


    logger.info(f"Profile updated successfully for user ID: {target_user_id}")
    return jsonify({"status": "success", "profile": result.get('profile')}), 200

@auth_routes.route('/api/auth/role', methods=['PUT'])
@admin_required
@validate_json_request(required_fields=['user_id', 'role'])
@handle_api_exception
def update_user_role():
    """Update user role (admin only)"""
    data = request.json
    user_id = data.get('user_id')
    role = data.get('role')
    
    logger.info(f"Role update request for user: {user_id} to role: {role}")
    
    # Validate role
    valid_roles = ['user', 'admin']
    if role not in valid_roles:
        return jsonify({
            "status": "error",
            "message": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        }), 400
    
    # Update role
    result = set_user_role(user_id, role)
    
    if result.get('status') == 'error':
        logger.warning(f"Role update failed: {result.get('message')}")
        return jsonify(result), 404
    
    logger.info(f"Role updated for user: {user_id}")
    return jsonify(result), 200