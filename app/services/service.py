from google.cloud import storage, firestore
from google.cloud.storage.blob import Blob
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timedelta
import logging
import requests  # For ML service interaction
import cv2
import numpy as np
from ultralytics import YOLO
import gc
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cloud Configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
ROMPES_BUCKET_NAME = os.getenv("ROMPES_BUCKET_NAME")
MODEL_BUCKET_NAME = os.getenv("MODEL_BUCKET_NAME", BUCKET_NAME)

rompes_storage_client = storage.Client()
storage_client = storage.Client()
firestore_client = firestore.Client()

# Firestore Collection
BATCH_COLLECTION = "vegetable_batches"
WEIGHTS_SUBCOLLECTION = "weights"

# Global model variable
model = None

def download_model_from_gcs():
    """Download ML model from Google Cloud Storage"""
    global model
    if model is not None:
        return model
    
    try:
        logger.info("Downloading ML model from Cloud Storage...")
        
        # Create local directory for model in /tmp (Cloud Run writable directory)
        model_dir = "/tmp/models/weights"
        os.makedirs(model_dir, exist_ok=True)
        
        # Download model file from GCS
        bucket = storage_client.bucket(MODEL_BUCKET_NAME)
        blob = bucket.blob("best.pt")
        
        local_model_path = os.path.join(model_dir, "best.pt")
        blob.download_to_filename(local_model_path)
        
        logger.info(f"Model downloaded to {local_model_path}")
        
        # Load the model
        model = YOLO(local_model_path)
        logger.info("Model loaded successfully")
        
        return model
        
    except Exception as e:
        logger.error(f"Error downloading/loading model: {str(e)}")
        raise

def get_model():
    """Get the ML model, downloading if necessary"""
    global model
    if model is None:
        model = download_model_from_gcs()
    return model

def upload_image(file, filename, bucket_name=None):
    try:
        bucket_name = bucket_name or BUCKET_NAME
        bucket = storage_client.bucket(bucket_name)
        file.seek(0)
        blob = bucket.blob(filename)
        blob.upload_from_string(file.read(), content_type=file.content_type)

        signed_url = blob.generate_signed_url(
            expiration=timedelta(minutes=15),
            method='GET'
        )

        logger.info(f"Image uploaded to {bucket_name} with URL: {signed_url}")
        return signed_url
    except Exception as e:
        logger.error(f"Image upload failed: {str(e)}")
        raise

def delete_image(filename, bucket_name=None):
    try:
        bucket_name = bucket_name or BUCKET_NAME
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        blob.delete()
        logger.info(f"Deleted image {filename} from bucket {bucket_name}")
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        raise

def identify_vegetable(image_url, batch_id=None):
    img = None
    image_array = None
    results = None
    filename = image_url.split('/')[-1].split('?')[0]  # Extract filename from URL

    try:
         # Get the model (download if not already loaded)
        current_model = get_model()
        with requests.get(image_url, stream=True) as resp:
            resp.raise_for_status()
            image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            # Use the downloaded model instead of the global one
            results = current_model(img)[0]

            detections = []
            for det in results.boxes.data:
                conf = float(det[4])
                class_id = int(det[5])
                detections.append({
                    'vegetable_type': results.names[class_id],
                    'confidence': round(conf, 2)
                })

            if not detections:
                logger.warning("No object detected")
                delete_image(filename)  # Delete image if no object detected
                return {"status": "error", "message": "No object detected"}

            detections.sort(key=lambda x: x['confidence'], reverse=True)
            best_detection = detections[0]

            # if best_detection['vegetable_type'] in ["kale", "bayam merah"] and best_detection['confidence'] >= 0.7:
            if best_detection['vegetable_type'] in ["kale", "bayam merah"]:

                best_detection["image_url"] = image_url
                best_detection["timestamp"] = datetime.utcnow().isoformat()

                if batch_id:
                    batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
                    batch_ref.update({
                        "vegetable_type": best_detection['vegetable_type'],
                        "confidence": best_detection['confidence'],
                        "image_url": image_url
                    })

                logger.info(f"Detected: {best_detection['vegetable_type']} with {best_detection['confidence']}")
                return best_detection
            else:
                logger.info(f"Detected vegetable is not kale or bayam merah or confidence is below threshold")
                delete_image(filename)  # Delete image if not kale/bayam merah
                return {"status": "error", "message": "bukan kale atau bayam merah"}

    except Exception as e:
        logger.error(f"Vegetable identification error: {str(e)}")
        # Try to delete image in case of error
        try:
            delete_image(filename)
        except:
            pass
        raise

    finally:
        # Explicitly release memory and clear PyTorch cache
        del img
        del image_array
        del results
        gc.collect()

#UNIFIED WEIGHING SESSION TESTING

def initiate_weighing_session(session_data):
    """Unified endpoint to initiate weighing session for both product and rompes"""
    try:
        session_id = str(uuid.uuid4())
        user_id = session_data.get('user_id')
        session_type = session_data.get('session_type')  # 'product' or 'rompes'
        
        if session_type not in ['product', 'rompes']:
            raise ValueError("session_type must be either 'product' or 'rompes'")
        
        # Add prefix to session_id based on type
        if session_type == 'product':
            prefixed_session_id = f"prod_{session_id}"
            collection_name = BATCH_COLLECTION  # "vegetable_batches"
        else:  # rompes
            prefixed_session_id = f"rompes_{session_id}"
            collection_name = "rompes_batches"
        
        # Create session in appropriate collection
        session_ref = firestore_client.collection(collection_name).document(prefixed_session_id)
        session_ref.set({
            "user_id": user_id,
            "session_type": session_type,
            "status": "in_progress",
            "created_at": datetime.utcnow(),
            "total_weight": 0
        })
        
        logger.info(f"Weighing session initiated: {prefixed_session_id} (type: {session_type})")
        
        return {
            "status": "initiated",
            "session_id": prefixed_session_id,
            "session_type": session_type,
            "message": f"{session_type.capitalize()} weighing session started"
        }
        
    except Exception as e:
        logger.error(f"Session initiation error: {str(e)}")
        raise

def get_user_weighing_history(user_id):
    """Get combined weighing history from both collections"""
    try:
        logger.info(f"Retrieving weighing history for user: {user_id}")
        
        all_sessions = []
        
        # Get product batches
        product_ref = firestore_client.collection(BATCH_COLLECTION)
        product_query = product_ref.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        
        for doc in product_query.stream():
            session_data = doc.to_dict()
            session_data['session_id'] = doc.id
            session_data['session_type'] = 'product'
            
            # Format timestamp
            if 'created_at' in session_data and session_data['created_at']:
                session_data['formatted_date'] = session_data['created_at'].strftime('%A, %d-%m-%Y')
            
            all_sessions.append({
                'session_id': doc.id,
                'session_type': 'product',
                'vegetable_type': session_data.get('vegetable_type', 'Unknown'),
                'total_weight': session_data.get('total_weight', 0),
                'image_url': session_data.get('image_url', ''),
                'formatted_date': session_data.get('formatted_date', ''),
                'status': session_data.get('status', ''),
                'notes': session_data.get('notes', '')
            })
        
        # Get rompes batches
        rompes_ref = firestore_client.collection('rompes_batches')
        rompes_query = rompes_ref.where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
        
        for doc in rompes_query.stream():
            session_data = doc.to_dict()
            session_data['session_id'] = doc.id
            session_data['session_type'] = 'rompes'
            
            # Format timestamp
            if 'created_at' in session_data and session_data['created_at']:
                session_data['formatted_date'] = session_data['created_at'].strftime('%A, %d-%m-%Y')
            
            all_sessions.append({
                'session_id': doc.id,
                'session_type': 'rompes',
                'vegetable_type': 'Rompes',  # Fixed type for rompes
                'total_weight': session_data.get('total_weight', 0),
                'image_url': session_data.get('image_url', ''),
                'formatted_date': session_data.get('formatted_date', ''),
                'status': session_data.get('status', ''),
                'notes': session_data.get('notes', '')
            })
        
        # Sort all sessions by creation date (most recent first)
        all_sessions.sort(key=lambda x: x.get('formatted_date', ''), reverse=True)
        
        logger.info(f"Found {len(all_sessions)} total weighing sessions for user {user_id}")
        return all_sessions
        
    except Exception as e:
        logger.error(f"Error retrieving weighing history: {str(e)}")
        raise

def get_weighing_session_detail(session_id):
    """Get detailed information about a specific weighing session"""
    try:
        logger.info(f"Retrieving details for session: {session_id}")
        
        # Determine session type and collection from prefix
        if session_id.startswith('prod_'):
            collection_name = BATCH_COLLECTION
            session_type = 'product'
        elif session_id.startswith('rompes_'):
            collection_name = 'rompes_batches'
            session_type = 'rompes'
        else:
            # Handle legacy IDs without prefix (assume product for backward compatibility)
            collection_name = BATCH_COLLECTION
            session_type = 'product'
        
        session_ref = firestore_client.collection(collection_name).document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            logger.warning(f"Session {session_id} not found")
            return {
                "status": "error",
                "message": "Weighing session not found"
            }
        
        session_data = session_doc.to_dict()
        session_data['session_id'] = session_id
        session_data['session_type'] = session_type
        
        # Format timestamps
        for time_field in ['created_at', 'completed_at']:
            if time_field in session_data and session_data[time_field]:
                session_data[f'formatted_{time_field}'] = session_data[time_field].strftime('%A, %d-%m-%Y %H:%M:%S')
        
        # Get individual weights for product sessions (rompes might not have subcollection)
        weights = []
        if session_type == 'product':
            weights_ref = session_ref.collection(WEIGHTS_SUBCOLLECTION)
            for weight_doc in weights_ref.order_by('timestamp').stream():
                weight_data = weight_doc.to_dict()
                if 'timestamp' in weight_data:
                    weight_data['formatted_time'] = weight_data['timestamp'].strftime('%H:%M:%S')
                weights.append(weight_data)
        
        session_data['weights'] = weights
        logger.info(f"Retrieved session {session_id} with {len(weights)} weight entries")
        
        return {
            "status": "success",
            "session": session_data
        }
        
    except Exception as e:
        logger.error(f"Error retrieving session details: {str(e)}")
        raise

def complete_weighing_session(session_data):
    """Complete a weighing session (works for both product and rompes)"""
    try:
        session_id = session_data.get('session_id')
        if not session_id:
            raise ValueError("session_id is required.")
        
        # Determine collection from prefix
        if session_id.startswith('prod_'):
            collection_name = BATCH_COLLECTION
            session_type = 'product'
        elif session_id.startswith('rompes_'):
            collection_name = 'rompes_batches'
            session_type = 'rompes'
        else:
            # Handle legacy IDs
            collection_name = BATCH_COLLECTION
            session_type = 'product'
        
        session_ref = firestore_client.collection(collection_name).document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            raise ValueError(f"Session with ID {session_id} does not exist.")
        
        update_payload = {
            "status": "completed",
            "completed_at": datetime.utcnow()
        }
        session_ref.update(update_payload)
        session_info = session_ref.get().to_dict()
        
        logger.info(f"Session completed: {session_id}")
        
        return {
            "session_id": session_id,
            "session_type": session_type,
            "user_id": session_info.get("user_id"),
            "status": session_info.get("status"),
            "created_at": session_info.get("created_at"),
            "completed_at": session_info.get("completed_at"),
            "vegetable_type": session_info.get("vegetable_type"),
            "total_weight": session_info.get("total_weight"),
            "confidence": session_info.get("confidence"),
            "image_url": session_info.get("image_url")
        }
        
    except Exception as e:
        logger.error(f"Session completion error: {str(e)}")
        raise