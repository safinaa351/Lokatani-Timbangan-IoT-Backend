# Flask Backend for Weight and Image Storage

This project is a simple Flask backend application designed to store weight data and images in Firebase. The API is structured to facilitate easy interaction with the Firebase services and is intended to be deployed on Google Cloud Run.

## Project Structure

```
flask-backend
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── routes.py
│   └── services
│       └── service.py
├── Dockerfile
├── cloudbuild.yaml
├── requirements.txt
└── README.md
```

### Description of Files

- **app/__init__.py**: Initializes the Flask application and sets up the application context.
- **app/main.py**: Entry point of the application that creates and runs the Flask app.
- **app/models.py**: Defines the data models for weight and image storage.
- **app/routes.py**: Contains the API routes and handlers for processing requests.
- **app/services/service.py**: Handles interactions with Firebase, Google Cloud Storage, and Firestore for uploading images, storing weight data, and processing rompes weighing.
- **Dockerfile**: Instructions for building the Docker image for the application.
- **cloudbuild.yaml**: Configuration for Google Cloud Build to automate the build and deployment process.
- **requirements.txt**: Lists the Python dependencies required for the project.

## Setup Instructions

1. **Clone the Repository**: 
   ```
   git clone <repository-url>
   cd flask-backend
   ```

2. **Install Dependencies**: 
   ```
   pip install -r requirements.txt
   ```

3. **Run the Application**: 
   ```
   python app/main.py
   ```

## Usage

- The API provides endpoints to upload weight data and images to Firebase.
- Ensure that you have configured Firebase credentials and set up the necessary Firebase services.

## Deployment

This application can be deployed on Google Cloud Run using Cloud Build. Ensure that your `cloudbuild.yaml` is properly configured to build and push the Docker image to the Container Registry.

## Dependencies

The project uses the following Python libraries:
- Flask
- Gunicorn
- google-cloud-storage
- google-cloud-firestore
- python-dotenv
- Pillow
- requests (for ML service interaction)

## License

This project is licensed under the MIT License.