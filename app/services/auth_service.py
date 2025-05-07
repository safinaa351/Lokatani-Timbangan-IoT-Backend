from google.cloud import firestore
from datetime import datetime
import logging
import uuid
import hashlib
import os
import re
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Firestore client
firestore_client = firestore.Client()

# Constants
USER_COLLECTION = "users"
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@lokatani\.id$'  # Adjust to your company domain

def hash_password(password, salt=None):
    if not salt:
        salt = os.urandom(32)
    
    key = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt, 100000
    )
    
    return {
        'key': base64.b64encode(key).decode('utf-8'),
        'salt': base64.b64encode(salt).decode('utf-8')
    }

def verify_password(stored_password, stored_salt, provided_password):
    stored_password = base64.b64decode(stored_password.encode('utf-8'))
    stored_salt = base64.b64decode(stored_salt.encode('utf-8'))
    verification_result = hash_password(provided_password, stored_salt)
    return base64.b64decode(verification_result['key'].encode('utf-8')) == stored_password

def create_user(email, password, name, role='user'):
    """Create a new user in Firestore"""
    try:
        # Input validation
        if not re.match(EMAIL_REGEX, email):
            logger.warning(f"Invalid email format for company domain: {email}")
            return {
                "status": "error",
                "message": "Email must be from the company domain (@lokatani.id)"
            }
        
        # Check if user already exists
        user_ref = firestore_client.collection(USER_COLLECTION)
        existing_user = user_ref.where('email', '==', email).limit(1).get()
        
        if len(list(existing_user)) > 0:
            logger.warning(f"Attempted registration with existing email: {email}")
            return {
                "status": "error",
                "message": "Email already registered"
            }
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user document
        user_id = str(uuid.uuid4())
        user_data = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "role": role,
            "password": password_hash['key'],
            "salt": password_hash['salt'],
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        # Save to Firestore
        user_ref.document(user_id).set(user_data)
        logger.info(f"New user created: {user_id}")
        
        # Return success without password data
        return {
            "status": "success",
            "user_id": user_id,
            "email": email,
            "name": name,
            "role": role,
            "message": "User registered successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return {
            "status": "error",
            "message": "An internal error occurred. Please try again later."
        }

def login_user(email, password):
    """Authenticate user credentials"""
    try:
        # Get user by email
        user_ref = firestore_client.collection(USER_COLLECTION)
        user_query = user_ref.where('email', '==', email).limit(1).get()
        
        if not user_query:
            logger.warning(f"Login attempt with non-existent email: {email}")
            return {
                "status": "error",
                "message": "Invalid email or password"
            }
        
        user_doc = list(user_query)[0]
        user_data = user_doc.to_dict()
        
        # Verify password
        stored_password = user_data.get('password')
        stored_salt = user_data.get('salt')
        
        if not verify_password(stored_password, stored_salt, password):
            logger.warning(f"Failed login attempt for email: {email}")
            return {
                "status": "error",
                "message": "Invalid email or password"
            }
        
        # Update last login
        user_doc.reference.update({
            "last_login": datetime.utcnow()
        })
        
        logger.info(f"User logged in: {user_data.get('user_id')}")
        
        # Return user data (excluding password)
        return {
            "status": "success",
            "user_id": user_data.get('user_id'),
            "email": email,
            "name": user_data.get('name'),
            "role": user_data.get('role'),
            "message": "Login successful"
        }
        
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return {
            "status": "error",
            "message": "An internal error occurred. Please try again later."
        }

def get_user_profile(user_id):
    """Get user profile data"""
    try:
        user_ref = firestore_client.collection(USER_COLLECTION).document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            logger.warning(f"Profile request for non-existent user: {user_id}")
            return {
                "status": "error",
                "message": "User not found"
            }
            
        user_data = user_doc.to_dict()
        
        # Return user profile without sensitive data
        return {
            "status": "success",
            "user_id": user_id,
            "email": user_data.get('email'),
            "name": user_data.get('name'),
            "role": user_data.get('role'),
            "created_at": user_data.get('created_at'),
            "last_login": user_data.get('last_login')
        }
        
    except Exception as e:
        logger.error(f"Error retrieving user profile: {str(e)}")
        raise

def update_user_profile(user_id, profile_data):
    """Update user profile fields"""
    try:
        user_ref = firestore_client.collection(USER_COLLECTION).document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            logger.warning(f"Update attempt for non-existent user: {user_id}")
            return {
                "status": "error",
                "message": "User not found"
            }
        
        # Remove fields that shouldn't be updated directly
        if 'password' in profile_data:
            del profile_data['password']
        if 'email' in profile_data:
            del profile_data['email']
        if 'user_id' in profile_data:
            del profile_data['user_id']
        if 'role' in profile_data:
            del profile_data['role']
        
        # Update only allowed fields
        if profile_data:
            profile_data['updated_at'] = datetime.utcnow()
            user_ref.update(profile_data)
            
            logger.info(f"Updated profile for user: {user_id}")
            return {
                "status": "success",
                "message": "Profile updated successfully"
            }
        else:
            logger.warning(f"No valid fields to update for user: {user_id}")
            return {
                "status": "warning",
                "message": "No valid fields to update"
            }
        
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise

def change_password(user_id, current_password, new_password):
    """Change user password"""
    try:
        user_ref = firestore_client.collection(USER_COLLECTION).document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            logger.warning(f"Password change attempt for non-existent user: {user_id}")
            return {
                "status": "error",
                "message": "User not found"
            }
            
        user_data = user_doc.to_dict()
        
        # Verify current password
        stored_password = user_data.get('password')
        stored_salt = user_data.get('salt')
        
        if not verify_password(stored_password, stored_salt, current_password):
            logger.warning(f"Invalid current password for user: {user_id}")
            return {
                "status": "error",
                "message": "Current password is incorrect"
            }
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update password in database
        user_ref.update({
            "password": password_hash['key'],
            "salt": password_hash['salt'],
            "password_updated_at": datetime.utcnow()
        })
        
        logger.info(f"Password changed for user: {user_id}")
        return {
            "status": "success",
            "message": "Password changed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise