from google.cloud import firestore
from datetime import datetime
import logging
import uuid
from firebase_admin import auth

logger = logging.getLogger(__name__)

# Firestore client
firestore_client = firestore.Client()
USER_COLLECTION = "users"

def get_or_create_user_profile(firebase_uid, email):
    """Get existing user profile or create new one for Firebase user"""
    try:
        # First, try to find user by firebase_uid
        user_ref = firestore_client.collection(USER_COLLECTION)
        user_query = user_ref.where('firebase_uid', '==', firebase_uid).limit(1).get()
        
        if user_query:
            user_doc = list(user_query)[0]
            user_data = user_doc.to_dict()
            logger.info(f"Found existing user profile for Firebase UID: {firebase_uid}")
            return user_data
        
        # If not found by firebase_uid, try to find by email (for migration)
        email_query = user_ref.where('email', '==', email).limit(1).get()
        
        if email_query:
            # Existing user from old system - update with firebase_uid
            user_doc = list(email_query)[0]
            user_data = user_doc.to_dict()
            
            # Update document with firebase_uid
            user_doc.reference.update({
                'firebase_uid': firebase_uid,
                'migrated_at': datetime.utcnow()
            })
            
            user_data['firebase_uid'] = firebase_uid
            logger.info(f"Migrated existing user to Firebase: {email}")
            return user_data
        
        # Create new user profile
        user_id = str(uuid.uuid4())
        
        # Get additional info from Firebase Auth
        firebase_user = auth.get_user(firebase_uid)
        display_name = firebase_user.display_name or email.split('@')[0]
        
        user_data = {
            "user_id": user_id,
            "firebase_uid": firebase_uid,
            "email": email,
            "name": display_name,
            "role": "user",  # Default role
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }
        
        # Save to Firestore
        user_ref.document(user_id).set(user_data)
        logger.info(f"Created new user profile for Firebase UID: {firebase_uid}")
        
        return user_data
        
    except Exception as e:
        logger.error(f"Error getting/creating user profile: {str(e)}")
        return None

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
        restricted_fields = ['firebase_uid', 'email', 'user_id', 'created_at']
        for field in restricted_fields:
            if field in profile_data:
                del profile_data[field]
        
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
            "firebase_uid": user_data.get('firebase_uid'),
            "email": user_data.get('email'),
            "name": user_data.get('name'),
            "role": user_data.get('role'),
            "created_at": user_data.get('created_at'),
            "last_login": user_data.get('last_login')
        }
        
    except Exception as e:
        logger.error(f"Error retrieving user profile: {str(e)}")
        raise

def set_user_role(user_id, role):
    """Set custom role for user (admin function)"""
    try:
        user_ref = firestore_client.collection(USER_COLLECTION).document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return {
                "status": "error",
                "message": "User not found"
            }
        
        # Update role
        user_ref.update({
            'role': role,
            'role_updated_at': datetime.utcnow()
        })
        
        # Optionally, set custom claims in Firebase Auth
        user_data = user_doc.to_dict()
        firebase_uid = user_data.get('firebase_uid')
        
        if firebase_uid:
            auth.set_custom_user_claims(firebase_uid, {'role': role})
        
        logger.info(f"Updated role for user {user_id} to {role}")
        return {
            "status": "success",
            "message": f"User role updated to {role}"
        }
        
    except Exception as e:
        logger.error(f"Error setting user role: {str(e)}")
        raise