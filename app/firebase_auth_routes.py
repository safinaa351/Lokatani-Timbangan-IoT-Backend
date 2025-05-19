from flask import Blueprint, request, jsonify
from app.services.firebase_service import FirebaseAuthService
from app.validators import validate_json_request, handle_api_exception

firebase_auth = Blueprint('firebase_auth', __name__)

@firebase_auth.route('/api/auth/register', methods=['POST'])
@validate_json_request(required_fields=['email', 'password', 'display_name'])
@handle_api_exception
def register():
    data = request.json
    return jsonify(FirebaseAuthService.create_user(
        email=data.get('email'),
        password=data.get('password'),
        display_name=data.get('display_name')
    ))

@firebase_auth.route('/api/auth/verify-token', methods=['POST'])
@validate_json_request(required_fields=['id_token'])
@handle_api_exception
def verify_token():
    data = request.json
    return jsonify(FirebaseAuthService.verify_token(data.get('id_token')))

@firebase_auth.route('/api/auth/profile/<user_id>', methods=['GET'])
@handle_api_exception
def get_profile(user_id):
    return jsonify(FirebaseAuthService.get_user_profile(user_id))