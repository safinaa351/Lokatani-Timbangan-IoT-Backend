import firebase_admin
from firebase_admin import auth, credentials
import logging
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get the path from the environment
firebase_creds_path = os.getenv("FIREBASE_ADMIN_CREDENTIALS")

# Check if the path is valid
if not firebase_creds_path or not os.path.exists(firebase_creds_path):
    raise ValueError("FIREBASE_ADMIN_CREDENTIALS not set or file not found.")

# Initialize Firebase Admin SDK
cred = credentials.Certificate(firebase_creds_path)
firebase_admin.initialize_app(cred)

logger = logging.getLogger(__name__)

# Constants
ALLOWED_DOMAINS = ['lokatani.id', 'mhsw.pnj.ac.id']
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@(?:lokatani\.id|mhsw\.pnj\.ac\.id)$'

class FirebaseAuthService:
    @staticmethod
    def create_user(email, password, display_name):
        try:
            # Validate email domain
            if not re.match(EMAIL_REGEX, email):
                return {
                    'status': 'error',
                    'message': f'Email must be from domains: {", ".join(ALLOWED_DOMAINS)}'
                }

            # Create user in Firebase
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                email_verified=False
            )

            # Send verification email
            verification_link = auth.generate_email_verification_link(email)
            # Implement email sending logic here

            return {
                'status': 'success',
                'user_id': user.uid,
                'email': user.email,
                'display_name': user.display_name
            }

        except auth.EmailAlreadyExistsError:
            return {'status': 'error', 'message': 'Email already registered'}
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return {'status': 'error', 'message': 'Registration failed'}

    @staticmethod
    def verify_token(id_token):
        try:
            decoded_token = auth.verify_id_token(id_token)
            return {
                'status': 'success',
                'user_id': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'email_verified': decoded_token.get('email_verified', False)
            }
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return {'status': 'error', 'message': 'Invalid token'}

    @staticmethod
    def get_user_profile(user_id):
        try:
            user = auth.get_user(user_id)
            return {
                'status': 'success',
                'user_id': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'email_verified': user.email_verified
            }
        except auth.UserNotFoundError:
            return {'status': 'error', 'message': 'User not found'}
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return {'status': 'error', 'message': 'Failed to get profile'}