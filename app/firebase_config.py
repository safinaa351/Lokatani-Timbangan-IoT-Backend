import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
        logger.info("Firebase Admin SDK already initialized")
    except ValueError:
        # Initialize Firebase Admin SDK
        # You can use service account key file or default credentials
        service_account_path = os.getenv('FIREBASE_ADMIN_CREDENTIALS')
        
        if service_account_path:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized with service account")
        else:
            # Use default credentials (for Cloud Run/GCP environment)
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized with default credentials")

# Initialize on import
initialize_firebase()