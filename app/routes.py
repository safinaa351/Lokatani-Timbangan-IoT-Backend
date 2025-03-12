from flask import Blueprint, request, jsonify
import imghdr
from app.services.service import upload_image, save_weight

routes = Blueprint('routes', __name__)

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    """Cek apakah file memiliki ekstensi gambar yang valid"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@routes.route('/')
def home():
    return "Tes modifikasi"

@routes.route('/upload_with_weight', methods=['POST'])
def upload_with_weight():
    """API untuk upload gambar & simpan berat sayur ke Firestore."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Cek ekstensi file
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only PNG, JPG, and JPEG are allowed."}), 400

    # Cek MIME type agar hanya file gambar yang bisa di-upload
    file_type = imghdr.what(file)
    if file_type not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Invalid file content. Only images are allowed."}), 400

    sayur_name = request.form.get("name")
    weight = request.form.get("weight")

    if not sayur_name or not weight:
        return jsonify({"error": "Missing 'name' or 'weight'"}), 400

    try:
        image_url = upload_image(file, file.filename)  # Upload gambar
        result = save_weight(sayur_name, int(weight), image_url)  # Simpan data ke Firestore
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes.route('/upload', methods=['POST'])
def upload_file():
    """API untuk upload gambar ke Cloud Storage."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Cek ekstensi file
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only PNG, JPG, and JPEG are allowed."}), 400

    # Cek MIME type
    file_type = imghdr.what(file)
    if file_type not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Invalid file content. Only images are allowed."}), 400

    try:
        file_url = upload_image(file, file.filename)
        return jsonify({"message": "Upload berhasil", "url": file_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
