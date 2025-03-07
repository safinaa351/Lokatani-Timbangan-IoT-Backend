from google.cloud import storage, firestore
import os
from datetime import datetime
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(BASE_DIR, "cloud-storage-key.json")

BUCKET_NAME = "img-sayur-lokatani"
storage_client = storage.Client()

# Setup Firestore
firestore_client = firestore.Client()
COLLECTION_NAME = "berat-sayuran"

def upload_image(file, filename):
    """Upload file ke Google Cloud Storage dan return URL-nya."""
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(file.read(), content_type=file.content_type)
    
    image_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return image_url

def save_weight(sayur_name, weight, image_url):
    """Simpan berat sayur ke Firestore."""
    sayur_id = str(uuid.uuid4())  # Generate ID unik
    doc_ref = firestore_client.collection(COLLECTION_NAME).document(sayur_name)
    doc_ref.set({
        "id": sayur_id,
        "name": sayur_name,
        "weight": weight,
        "image_url": image_url,
        "timestamp": datetime.utcnow()  # Simpan waktu UTC
    })

    return {
        "message": "Data berhasil disimpan",
        "id": sayur_id,
        "name": sayur_name,
        "weight": weight,
        "image_url": image_url,
        "timestamp": datetime.utcnow().isoformat()  # Format timestamp biar rapi
    }