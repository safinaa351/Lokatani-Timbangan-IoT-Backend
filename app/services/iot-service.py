import logging
import os
import requests
import tensorflow as tf
import numpy as np
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VegetableMLService:
    def __init__(self, model_path=None):
        """
        Initialize ML service with optional model loading
        
        Args:
            model_path (str, optional): Path to pre-trained model
        """
        self.model = None
        # MODIFICATION: Updated to match actual vegetables
        self.vegetable_classes = ['kale', 'red_spinach']
        
        try:
            # Optional: Load TensorFlow model
            if model_path and os.path.exists(model_path):
                logger.info(f"Loading ML model from {model_path}")
                self.model = tf.keras.models.load_model(model_path)
            else:
                logger.warning("No pre-trained model found. Using fallback identification.")
        except Exception as e:
            logger.error(f"Model loading error: {str(e)}")
    
    def predict_vegetable(self, image_tensor):
        """
        Predict vegetable type from image
        
        Args:
            image_tensor (np.array): Preprocessed image
        
        Returns:
            dict: Prediction results
        """
        try:
            # Fallback prediction if no model
            if self.model is None:
                logger.warning("Using fallback prediction method")
                return self._fallback_prediction()
            
            # ML Model Prediction
            predictions = self.model.predict(image_tensor)
            predicted_class_index = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_index])
            
            vegetable_type = self.vegetable_classes[predicted_class_index]
            
            # MODIFICATION: Removed all_probabilities
            result = {
                'vegetable_type': vegetable_type,
                'confidence': confidence
            }
            
            logger.info(f"Vegetable identified: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return self._fallback_prediction()
    
    def _fallback_prediction(self):
        """
        Fallback prediction method when ML model is unavailable
        
        Returns:
            dict: Fallback prediction
        """
        logger.warning("Using fallback prediction")
        return {
            'vegetable_type': 'unknown',
            'confidence': 0.5
        }
    
    def process_vegetable_identification(self, image_url, batch_id=None):
        """
        Complete vegetable identification workflow
        
        Args:
            image_url (str): URL of vegetable image
            batch_id (str, optional): Associated batch ID
        
        Returns:
            dict: Comprehensive identification result
        """
        try:
            logger.info(f"Starting vegetable identification for image: {image_url}")
            
            # Preprocess image
            image_tensor = self.preprocess_image(image_url)
            
            # Predict vegetable
            prediction = self.predict_vegetable(image_tensor)
            
            # Optional: Save to Firestore if batch_id provided
            if batch_id:
                self._save_identification_to_firestore(batch_id, prediction)
            
            return prediction
        
        except Exception as e:
            logger.error(f"Vegetable identification workflow error: {str(e)}")
            return self._fallback_prediction()
    
    def _save_identification_to_firestore(self, batch_id, prediction):
        """
        Save identification results to Firestore
        
        Args:
            batch_id (str): Batch document ID
            prediction (dict): Prediction results
        """
        try:
            from google.cloud import firestore
            
            firestore_client = firestore.Client()
            batch_ref = firestore_client.collection('vegetable_batches').document(batch_id)
            
            # MODIFICATION: Simplified ML identification update
            batch_ref.update({
                'ml_identification': {
                    'vegetable_type': prediction.get('vegetable_type', 'unknown'),
                    'confidence': prediction.get('confidence', 0)
                }
            })
            
            logger.info(f"Identification saved for batch: {batch_id}")
        
        except Exception as e:
            logger.error(f"Firestore saving error: {str(e)}")

# Instantiate ML Service
vegetable_ml_service = VegetableMLService()