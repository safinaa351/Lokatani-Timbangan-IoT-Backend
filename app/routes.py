from flask import Blueprint, request, jsonify
from app.services.service import upload_image, save_weight

routes = Blueprint('routes', __name__)

@routes.route('/')
def home():
    return "Docker build berhasil!"

@routes.route('/upload_with_weight', methods=['POST'])
def upload_with_weight():
    """API untuk upload gambar & simpan berat sayur ke Firestore."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

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

'''
@routes.route('/upload', methods=['POST'])
def upload_file():
    """API untuk upload gambar ke Cloud Storage."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        file_url = upload_image(file, file.filename)
        return jsonify({"message": "Upload berhasil", "url": file_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@routes.route('/add_weight', methods=['POST'])
def add_weight():
    """API untuk menyimpan berat sayur ke Firestore."""
    data = request.get_json()
    if not data or "name" not in data or "weight" not in data:
        return jsonify({"error": "Request harus berisi 'name' dan 'weight'"}), 400

    try:
        result = save_weight(data["name"], data["weight"])
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500'
'''
