from google.cloud import storage, firestore
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timedelta
import logging
import requests  # For ML service interaction
import cv2
import numpy as np
from ultralytics import YOLO

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cloud Configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL")

storage_client = storage.Client()
firestore_client = firestore.Client()

# Firestore Collection
BATCH_COLLECTION = "vegetable_batches"
WEIGHTS_SUBCOLLECTION = "weights"

# Initialize YOLOv8 model
model = YOLO('yolov8s.pt')

def upload_image(file, filename):
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(file.read(), content_type=file.content_type)
        # Generate signed URL yang bisa diakses temporary
        image_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="GET"
        )
        logger.info(f"Image uploaded successfully: {image_url}")
        return image_url
    except Exception as e:
        logger.error(f"Image upload failed: {str(e)}")
        raise

def detect_weight(weight_data):
    try:
        # Basic validation
        if weight_data.get('current_weight', 0) <= 0:
            logger.warning("Invalid weight detected")
            return {"status": "error", "message": "Invalid weight"}
        
        logger.info(f"Weight detected: {weight_data['current_weight']} grams")
        return {
            "status": "detected",
            "weight": weight_data['current_weight'],
            "notification_required": True
        }
    except Exception as e:
        logger.error(f"Weight detection error: {str(e)}")
        raise

def stabilize_weight(weight_data):
    try:
        batch_id = weight_data.get('batch_id')
        stabilized_weight = weight_data.get('stabilized_weight')
        
        # Reference to batch document
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        weights_ref = batch_ref.collection(WEIGHTS_SUBCOLLECTION)
        
        # Create weight entry
        weight_entry = {
            "weight": stabilized_weight,
            "timestamp": datetime.utcnow(),
        }
        
        # Add to weights subcollection
        weights_ref.add(weight_entry)
        
        # Update total weight in the batch document
        batch_ref.update({
            "total_weight": firestore.Increment(stabilized_weight)
        })
        
        return {
            "status": "stabilized",
            "batch_id": batch_id,
            "weight": stabilized_weight
        }
    except Exception as e:
        logger.error(f"Weight stabilization error: {str(e)}")
        raise

def initiate_batch(batch_data):
    try:
        batch_id = str(uuid.uuid4())
        user_id = batch_data.get('user_id')

        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        batch_ref.set({
            "user_id": user_id,
            "status": "in_progress",
            "created_at": datetime.utcnow(),
            "total_weight": 0
        })
        
        logger.info(f"Batch initiated: {batch_id}")
        return {
            "status": "initiated",
            "batch_id": batch_id,
            "message": "Batch tracking started"
        }
    except Exception as e:
        logger.error(f"Batch initiation error: {str(e)}")
        raise

def complete_batch(batch_data):
    try:
        batch_id = batch_data.get('batch_id')
        if not batch_id:
            raise ValueError("batch_id is required.")
        
        # Reference to batch document
        batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
        batch_doc = batch_ref.get()
        if not batch_doc.exists:
            raise ValueError(f"Batch with ID {batch_id} does not exist.")
        
        # Get full batch info after update
        batch_info = batch_ref.get().to_dict()
        vegetable_type = batch_info.get("vegetable_type")  # From ML mock

        # Prepare update payload
        update_payload = {
            "status": "completed",
            "completed_at": datetime.utcnow()
        }
        
        # Update batch document
        batch_ref.update(update_payload)
        
        logger.info(f"Batch completed: {batch_id}")
        return {
            "batch_id": batch_id,
            "user_id": batch_info.get("user_id"),
            "status": "completed",
            "created_at": batch_info.get("created_at"),
            "completed_at": update_payload["completed_at"],
            "vegetable_type": vegetable_type,
            "total_weight": batch_info.get("total_weight"),
            "confidence": batch_info.get("confidence"),
            "image_url": batch_info.get("image_url")
        }
    except Exception as e:
        logger.error(f"Batch completion error: {str(e)}")
        raise


def identify_vegetable(image_url, batch_id):
    try:
        # Download using signed URL
        resp = requests.get(image_url, stream=True)
        resp.raise_for_status()
        
        # Convert image from URL to cv2 format
        image_array = np.asarray(bytearray(resp.content), dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        # Perform detection
        results = model(img)[0]
        
        # Get detection with highest confidence
        best_detection = None
        highest_conf = 0
        
        for detection in results.boxes.data:
            confidence = float(detection[4])
            if confidence > highest_conf:
                highest_conf = confidence
                class_id = int(detection[5])
                best_detection = {
                    'class': results.names[class_id],
                    'confidence': round(confidence * 100, 2)
                }
        
        if best_detection is None:
            return {'message': 'No objects detected'}
        
        # Update Firestore if batch_id is provided
        if batch_id:
            batch_ref = firestore_client.collection(BATCH_COLLECTION).document(batch_id)
            batch_ref.update({
                "detected_object": best_detection['class'],
                "confidence": best_detection['confidence'],
                "image_url": image_url
            })
            
        return {
            'detected_object': best_detection['class'],
            'confidence': best_detection['confidence'],
            'batch_id': batch_id,
            'image_url': image_url
        }

    except Exception as e:
        logger.error(f"Error in object detection: {str(e)}")
        raise Exception("Failed to process image")
