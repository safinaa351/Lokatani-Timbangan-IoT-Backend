from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import logging
from app.validators import (
    validate_uploaded_file, validate_json_request, handle_api_exception,
    validate_numeric, validate_string
)
from app.firebase_auth.firebase_middleware import firebase_token_required

from app.services.service import (
    upload_image,
    identify_vegetable,
    initiate_weighing_session,
    complete_weighing_session,
    get_user_weighing_history,
    get_weighing_session_detail
)

routes = Blueprint('routes', __name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@routes.route('/')
def home():
    """Basic health check endpoint"""
    logger.info("Home endpoint accessed")
    return jsonify({
        "status": "success",
        "message": "Backend is running",
        "service": "IoT Vegetable Weighing System",
        "version": "3.0.0",
        "auth": "Firebase Authentication"}), 200

@routes.route('/api/ml/identify-vegetable', methods=['POST'])
@firebase_token_required
@handle_api_exception
def process_vegetable_identification():
    logger.info("Vegetable identification request received")
    
    if 'file' not in request.files:
        logger.warning("No file part in the request")
        return jsonify({
            "status": "error",
            "message": "No file part in the request"
        }), 400

    file = request.files['file']
    # Now accepts either batch_id (legacy) or session_id (new)
    batch_id = request.form.get('batch_id') or request.form.get('session_id')
    
    # Validate batch_id if provided
    if batch_id is not None:
        error = validate_string(batch_id, 'Session ID')
        if error:
            return jsonify({"status": "error", "message": error}), 400

    # Validate image file
    error = validate_uploaded_file(file)
    if error:
        logger.warning(f"File validation failed: {error}")
        return jsonify({"status": "error", "message": error}), 400

    # Process image and identify vegetable
    safe_filename = secure_filename(file.filename)
    logger.info(f"Processing image: {safe_filename}")
    
    image_url = upload_image(file, safe_filename)
    identification_result = identify_vegetable(image_url, batch_id)

    logger.info(f"Vegetable identification result: {identification_result}")
    return jsonify(identification_result), 200

# UPDATED HISTORY ENDPOINT - Now returns both product and rompes sessions
@routes.route('/api/weighing/history', methods=['GET'])
@firebase_token_required
@handle_api_exception
def get_user_weighing_sessions():
    logger.info(f"Fetching weighing history")
    
    # Get the authenticated user's ID from the token
    authenticated_user_id = request.user.get('firebase_uid')
    if not authenticated_user_id:
         logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
         return jsonify({
             "status": "error",
             "message": "Authentication failed or user ID not available"
         }), 500

    logger.info(f"Fetching weighing history for user: {authenticated_user_id}")
        
    sessions = get_user_weighing_history(authenticated_user_id)
    logger.info(f"Retrieved {len(sessions)} weighing sessions for user {authenticated_user_id}")
    
    return jsonify({"status": "success", "sessions": sessions}), 200

@routes.route('/api/weighing/<session_id>', methods=['GET'])
@firebase_token_required
@handle_api_exception
def get_session_details(session_id):
    logger.info(f"Fetching details for session: {session_id}")
    
    if not session_id:
        return jsonify({"status": "error", "message": "Session ID is required"}), 400
    
    # Get the authenticated user's ID from the token
    authenticated_user_id = request.user.get('firebase_uid')
    if not authenticated_user_id:
         logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
         return jsonify({
             "status": "error",
             "message": "Authentication failed or user ID not available"
         }), 500

    session_details_result = get_weighing_session_detail(session_id)
    
    # Check if session exists
    if session_details_result.get('status') == 'error':
        logger.warning(f"Session {session_id} not found: {session_details_result.get('message', 'Unknown error')}")
        return jsonify(session_details_result), 404
    
    session_data = session_details_result.get('session')
    if not session_data:
        return jsonify({"status": "error", "message": "Session data not found"}), 404
    
    # Verify user owns the session
    session_owner_id = session_data.get('user_id')
    if session_owner_id != authenticated_user_id and request.user.get('role') != 'admin':
        logger.warning(f"User {authenticated_user_id} attempted to access session {session_id} belonging to user {session_owner_id}")
        return jsonify({
            "status": "error",
            "message": "You can only view your own sessions or you are not authorized"
        }), 403
        
    logger.info(f"Retrieved details for session: {session_id}")
    return jsonify(session_details_result), 200

#UNIFIED WEIGHING SESSION TESTING
@routes.route('/api/weighing/initiate', methods=['POST'])
@firebase_token_required
@validate_json_request(required_fields=['session_type'])
@handle_api_exception
def initiate_weighing():
    data = request.json or {}
    logger.info(f"Weighing session initiation request: {data}")
    
    # Get user_id directly from the authenticated token
    authenticated_user_id = request.user.get('firebase_uid')
    
    if not authenticated_user_id:
        logger.error("Authenticated user ID (firebase_uid) not found on request.user.")
        return jsonify({
            "status": "error",
            "message": "Authentication failed or user ID not available"
        }), 500
    
    # Validate session_type
    session_type = data.get('session_type')
    if session_type not in ['product', 'rompes']:
        return jsonify({
            "status": "error",
            "message": "session_type must be either 'product' or 'rompes'"
        }), 400
    
    # For rompes sessions, vegetable_type is required
    if session_type == 'rompes':
        vegetable_type = data.get('vegetable_type')
        if not vegetable_type:
            return jsonify({
                "status": "error",
                "message": "vegetable_type is required for rompes sessions"
            }), 400
        
        # Validate vegetable_type
        if vegetable_type not in ['kale', 'bayam merah']:
            return jsonify({
                "status": "error",
                "message": "vegetable_type must be either 'kale' or 'bayam merah'"
            }), 400
    
    logger.info(f"Authenticated user ID (firebase_uid): {authenticated_user_id}")

    # Force the user_id to be the authenticated user's ID for security
    data['user_id'] = authenticated_user_id
    
    # Initiate weighing session
    session_info = initiate_weighing_session(data)
    
    logger.info(f"Weighing session initiated: {session_info}")
    return jsonify(session_info), 200

# UPDATED COMPLETION ENDPOINT - Now works for both types
@routes.route('/api/weighing/complete', methods=['POST'])
@firebase_token_required
@validate_json_request(required_fields=['session_id'])
@handle_api_exception
def complete_weighing():
    data = request.json
    logger.info(f"Weighing session completion request: {data}")
    
    # Validate session_id
    error = validate_string(data['session_id'], 'Session ID')
    if error:
        return jsonify({"status": "error", "message": error}), 400
    
    # Complete weighing session
    session_result = complete_weighing_session(data)
    
    logger.info(f"Weighing session completed: {session_result}")
    return jsonify(session_result), 200