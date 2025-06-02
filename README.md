# Lokatani IoT Weight and Image Management Backend

This project is the backend API for Lokatani's IoT-based smart scales, designed to streamline the vegetable weighing process. It receives weight data and images from IoT devices, stores them securely in Google Cloud services (Firestore, and Cloud Storage), and manages weighing sessions. This system aims to improve efficiency and accuracy in agricultural product handling.

## Project Structure

```
flask-backend
├── app/                    # Contains the core application logic
│   ├── __init__.py       # Application factory
│   ├── routes.py         # Main API routes for user interactions
│   ├── routes_iot.py     # IoT-specific routes for device communication
│   ├── validators.py     # Request validation logic
│   ├── services/         # Business logic and external service interactions
│   │   ├── service.py    # Main services (Firebase, Cloud Storage, etc.)
│   │   └── iot_service.py # IoT device services
├── main.py              # Application entry point
├── Dockerfile           # Container configuration
├── cloudbuild.yaml      # Google Cloud Build config
├── requirements.txt     # Python dependencies
└── README.md            # Documentation
```

### Description of Files

-   **app/__init__.py**: Initializes the Flask application and sets up the application context.
-   **app/main.py**: The entry point of the application. It creates and starts the Flask app.
-   **app/models.py**: Defines the data models for weight data, images, and other relevant entities.
-   **app/routes.py**: Contains the API routes and handlers for processing requests from users or external systems.
-   **app/routes_iot.py**: Contains the API routes and handlers specifically for processing requests from IoT devices.
-   **app/validators.py**: Contains the request validation logic for both user and IoT requests.
-   **app/services/service.py**: Handles interactions with Firebase services (Authentication, Firestore, Cloud Storage) for uploading images, storing weight data, and managing weighing sessions.
-   **app/services/iot_service.py**: Handles interactions from IoT devices to the backend, processing lightweight payloads (e.g., sensor readings, device status).
-   **Dockerfile**: Instructions for building the Docker image for the application.
-   **cloudbuild.yaml**: Configuration for Google Cloud Build to automate the build and deployment process.
-   **requirements.txt**: Lists the Python dependencies required for the project.


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

### API Endpoints

#### Authentication
- `POST /api/auth/register`: Register a new user
- `POST /api/auth/login`: Login existing user
- `GET /api/auth/profile/<user_id>`: Get user profile information
- `PUT /api/auth/profile`: Update user profile information
- `PUT /api/auth/password`: Change user password

#### Batch Management
- `POST /api/batch/initiate`: Start a new batch weighing session
- `POST /api/batch/complete`: Complete a batch weighing session
- `GET /api/batches/history`: Get batch history for a user
- `GET /api/batches/<session_id>`: Get detailed information about a specific batch

#### IoT Device
- `POST /api/iot/weight`: Process weight data from IoT device
- `POST /api/iot/status`: Update IoT device status

#### Image Processing
- `POST /api/ml/identify-vegetable`: Process and identify vegetable in image
- `POST /api/rompes/process`: Process rompes weighing with image

## Deployment

This application is designed to be deployed on Google Cloud Run, a serverless platform that automatically scales based on demand. Cloud Build is used to automate the build and deployment process.

1.  **Build:** Cloud Build uses the `cloudbuild.yaml` file to build the Docker image.
2.  **Push:** The Docker image is pushed to the Google Container Registry.
3.  **Deploy:** Cloud Run deploys the image from the Container Registry.


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