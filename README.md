# Lokatani IoT Weight and Image Management Backend

Backend API for Lokatani's IoT-based smart scales. This service acts as the central hub, handling data ingestion from IoT devices, managing weighing sessions (both standard product and 'rompes' types), providing secure user access via Firebase Authentication, storing data securely in Google Cloud Platform (GCP) services (Firestore and Cloud Storage), and performing ML-based vegetable identification using a local YOLO model.

Built with Flask, Gunicorn, and leveraging Firebase Authentication, Google Cloud Firestore, and Google Cloud Storage. Designed for serverless deployment on Google Cloud Run.

For testing APIs, please visit this link : https://lokascale-frontend-web.vercel.app/

## ✨ Features

*   **IoT Data Ingestion:** Receive weight data and device status updates from IoT scales via a dedicated, API-key-secured endpoint.
*   **Unified Weighing Sessions:** Support for standard product weighing sessions and specialized 'rompes' sessions, managing their lifecycle and data within Firestore.
*   **Image Upload & Storage:** Securely upload images (associated with sessions) and store them in designated Google Cloud Storage buckets.
*   **Firebase Authentication:** Secure user access to non-IoT API endpoints using Firebase ID tokens.
*   **User Profile Management:** Store and retrieve user profiles in Firestore, linked to Firebase UIDs.
*   **ML Vegetable Identification:** Process uploaded images using a YOLO model downloaded from GCS to identify vegetable types within the images.
*   **Weighing Session Management API:** Endpoints for authenticated users to initiate (handled by IoT device via active session mechanism), complete, view history, and get detailed information about their weighing sessions.
*   **Rate Limiting:** Protect API endpoints from excessive requests to ensure stability and prevent abuse.
*   **CORS Enabled:** Allow frontend applications hosted on different origins to securely interact with the API.
*   **Google Cloud Integration:** Seamless integration with core GCP services: Firestore (database), Cloud Storage (file storage), and Cloud Run (serverless deployment).
*   **Jakarta Timezone Standard:** All timestamps stored and managed by the backend adhere to the Jakarta timezone (UTC+7) for consistency with local operations.

## 🏗️ System Architecture

The system follows a microservice-like pattern, with the Flask backend serving as a central API gateway and processing engine.

*   **API Layer:** Flask handles incoming HTTP requests from both IoT devices and frontend user applications.
*   **Authentication/Authorization:** Firebase Authentication secures user endpoints, while a custom API key validates IoT device requests. Role-based access control is available via Firestore user profiles.
*   **Business Logic:** Service modules encapsulate logic for processing IoT data, managing weighing sessions, interacting with GCP services, and executing ML inference.
*   **Data Storage:**
    *   **Firestore:** Used for structured data like user profiles, weighing session metadata, and individual weight records within sessions.
    *   **Cloud Storage:** Used for storing larger binary data, specifically uploaded images associated with sessions and the ML model file (`best.pt`).
*   **ML Processing:** The YOLO model is downloaded from Cloud Storage to the `/tmp` directory (Cloud Run's writable filesystem) upon application startup or first use, allowing for low-latency local inference.
*   **Deployment:** The application is containerized using Docker and deployed to Google Cloud Run, leveraging its serverless, autoscaling capabilities. Gunicorn is used as the production WSGI server within the container.

This architecture provides scalability, leverages managed GCP services for data persistence, and separates concerns between the API, business logic, and infrastructure interactions.

## 💻 Technology Stack

*   **Web Framework:** Flask
*   **WSGI Server:** Gunicorn
*   **Database:** Google Cloud Firestore
*   **File Storage:** Google Cloud Storage
*   **Authentication:** Firebase Authentication, Custom API Key
*   **ML Framework:** PyTorch (CPU), Ultralytics YOLO
*   **Image Processing:** Pillow, OpenCV-Python-headless
*   **Rate Limiting:** Flask-Limiter
*   **CORS:** Flask-CORS
*   **Environment Management:** python-dotenv
*   **Google Cloud SDKs:** `google-cloud-firestore`, `google-cloud-storage`
*   **Firebase SDK:** `firebase-admin`
*   **Networking:** Requests

## 📁 Project Structure

```
./
├── app/                    # Core application logic
│   ├── __init__.py       # Application factory, config (CORS, Limiter), Blueprint registration
│   ├── routes.py         # Main API routes (ML, Weighing Sessions Management)
│   ├── routes_iot.py     # IoT-specific routes (Weight Data Ingestion, Status Updates)
│   ├── routes_auth.py    # Authentication and User Profile routes
│   ├── validators.py     # Request data validation logic (JSON, Files, API Key) and decorators
│   ├── firebase_config.py # Firebase Admin SDK initialization logic
│   ├── firebase_auth/    # Firebase Authentication middleware
│   │   └── firebase_middleware.py # Decorators for Firebase token validation and role checks
│   └── services/         # Business logic, service interactions (GCP, ML)
│       ├── service.py    # Core services (GCS, Firestore, ML Model loading, Session Management)
│       ├── iot_service.py # IoT device data processing logic (Weight, Status, Active Session)
│       └── user_service.py # User profile management logic (Firestore, Firebase Auth integration)
├── main.py              # Application entry point (loads dotenv, initializes Flask app)
├── Dockerfile           # Container configuration for deployment
├── requirements.txt     # Python dependencies list
└── README.md            # Project documentation (this file)
```

### Description of Key Files and Directories

*   **`app/`**: Contains all the Flask application code organized into modules.
*   **`app/__init__.py`**: Sets up the Flask application instance, initializes extensions like CORS and Limiter, and registers blueprints for different route groups, acting as an application factory.
*   **`app/routes.py`**: Defines API endpoints for user-facing features such as ML identification and general weighing session interactions (history, detail).
*   **`app/routes_iot.py`**: Defines API endpoints specifically designed for secure communication with IoT devices, handling weight data and device status updates.
*   **`app/routes_auth.py`**: Defines API endpoints related to user authentication and profile management, primarily interacting with Firebase Auth and the Firestore user collection.
*   **`app/validators.py`**: Contains utility functions and decorators for validating incoming request data, including JSON payloads, file uploads, and API keys, ensuring data integrity and security.
*   **`app/firebase_config.py`**: Handles the initialization of the Firebase Admin SDK, allowing the backend to interact with Firebase services like Authentication and Firestore.
*   **`app/firebase_auth/firebase_middleware.py`**: Contains custom Flask decorators (`@firebase_token_required`, `@admin_required`) used to protect routes by validating Firebase ID tokens and checking user roles.
*   **`app/services/`**: Houses the business logic and functions responsible for interacting with external services (Firestore, Cloud Storage, ML Model inference) and orchestrating core application workflows.
*   **`app/services/service.py`**: Implements core functionalities including interacting with Cloud Storage for image and model handling, managing higher-level weighing session logic (like initiation/completion), and running ML identification.
*   **`app/services/iot_service.py`**: Contains the specific logic for processing data received from IoT devices, such as logging weight measurements and managing device status updates within Firestore, and determining the active session for a device.
*   **`app/services/user_service.py`**: Manages user profiles stored in Firestore, including retrieving, creating (integrating with Firebase Auth upon first login), and updating user information.
*   **`main.py`**: The primary entry point of the application, responsible for loading environment variables and running the Flask app instance, typically using Gunicorn in a production environment.
*   **`Dockerfile`**: Defines the steps required to build a portable Docker container image for the application, including installing dependencies and configuring the startup command.
*   **`requirements.txt`**: Lists all the Python libraries and their versions required by the project, ensuring reproducible environments.

## 🌐 API Endpoints

All API endpoints are prefixed with `/api/`.

### Authentication & User Profile (`/api/auth/`)

*   `GET /api/auth/profile/<user_id>`: Retrieve a user's profile information by their Firebase UID. Requires user authentication.
*   `PUT /api/auth/profile`: Update the authenticated user's profile information. Requires user authentication.

### Weighing Session Management (`/api/weighing/`)

*   `GET /api/weighing/history`: Retrieve the weighing session history (including both product and rompes sessions) for the authenticated user. Requires user authentication.
*   `GET /api/weighing/<session_id>`: Get detailed information for a specific weighing session (product or rompes). Requires user authentication.

### IoT Device Communication (`/api/iot/`)

*   `POST /api/iot/weight`: Endpoint for IoT devices to send weight measurement data. Requires API Key authorization.
*   `GET /api/iot/active-session`: Endpoint for IoT devices to request details about the most recent active weighing session assigned. Requires API Key authorization.
*   `POST /api/iot/status`: Endpoint for IoT devices to send status updates (e.g., connectivity). Requires API Key authorization.

### Image Processing & ML (`/api/ml/`)

*   `POST /api/ml/identify-vegetable`: Upload an image file and trigger ML-based vegetable identification. Can optionally link the image and result to a weighing session. Requires user authentication.

### General

*   `GET /`: Basic health check endpoint to verify the service is running.

## 🌊 Data Flow

1.  **IoT Device Interaction:**
    *   IoT device sends weight data or status updates to `/api/iot/*` endpoints.
    *   Backend validates API key.
    *   `iot_service` processes data and writes to Firestore (e.g., `weights` subcollection, `iot_devices` collection).
    *   IoT device queries `/api/iot/active-session`.
    *   `iot_service` queries Firestore for 'in_progress' sessions and returns the most recent.
2.  **Frontend User Interaction:**
    *   User logs in via Firebase Auth on the frontend, obtains an ID token.
    *   Frontend sends requests to `/api/auth/*`, `/api/weighing/*`, `/api/ml/*`, `/api/rompes/*` with the Firebase ID token in the `Authorization` header.
    *   `firebase_middleware` intercepts the request, verifies the token with Firebase Auth SDK, and retrieves/creates the user profile in Firestore via `user_service`.
    *   Validated requests proceed to the respective route handlers.
    *   Routes call `services` (e.g., `user_service`, `service`).
    *   `services` interact with Firestore (profiles, sessions, history) and Cloud Storage (image uploads, ML model).
    *   ML routes (`/api/ml/identify-vegetable`, `/api/rompes/process`) trigger ML model loading (from GCS if not cached) and inference via `service`.
    *   Results are returned to the frontend.

## 🔌 Integration Points

*   **Firebase Authentication:** Used directly via the `firebase-admin` SDK for verifying user ID tokens received from frontend clients and managing user records (implicitly via profile get/create).
*   **Google Cloud Firestore:** The primary database for structured data including user profiles, weighing session metadata, and detailed weight records. Accessed via `google-cloud-firestore` SDK.
*   **Google Cloud Storage:** Used for storing uploaded images (associated with sessions) and hosting the ML model file (`best.pt`) for backend download. Accessed via `google-cloud-storage` SDK.
*   **Google Cloud Run:** The target environment for serverless deployment of the Docker container. The application is designed to be stateless (except for the `/tmp` filesystem for the ML model) to leverage Cloud Run's scaling.

## 🏎️ Performance Considerations

*   **Cloud Run Scaling:** The serverless nature of Cloud Run allows the application to scale horizontally based on request load. However, cold starts can occur, particularly impacting latency for the first request after a period of inactivity.
*   **ML Model Loading:** The ML model (`best.pt`) is downloaded from Cloud Storage to the `/tmp` directory. This download happens either on application startup or the first time the model is needed. This can contribute to cold start latency on ML-heavy endpoints, especially if the container instance has been idle and spun down. Subsequent ML requests on an active container instance will use the cached model in `/tmp`.
*   **Gunicorn Workers:** The `Dockerfile` specifies `gunicorn` with multiple workers (`-w 2`), allowing the application to handle concurrent requests efficiently within a single container instance. `--max-requests` and `--max-requests-jitter` are used to mitigate potential memory leaks or resource exhaustion by periodically restarting workers.
*   **Database/Storage Latency:** Performance for data operations depends on Firestore and Cloud Storage read/write speeds and data modeling efficiency.
*   **Rate Limiting:** Flask-Limiter is used to prevent excessive requests from individual IP addresses, protecting backend resources.

## 🛡️ Security Aspects

*   **Firebase Authentication:** User-facing APIs are protected by validating Firebase ID tokens, ensuring only authenticated users can access their data and perform permitted actions.
*   **API Key Authorization:** IoT-specific endpoints are secured using a shared secret API key, validated via a custom decorator, preventing unauthorized devices from injecting data or querying sessions.
*   **Role-Based Authorization:** The framework includes an `@admin_required` decorator, allowing specific routes to be restricted to users with an 'admin' role defined in their Firestore profile.
*   **Input Validation:** Request data, including JSON payloads and uploaded files, is validated (`validators.py`) to prevent common vulnerabilities like injection attacks and ensure data integrity.
*   **Secure Credential Handling:** The application utilizes Google Cloud service accounts with scoped permissions to access GCP and Firebase services. While local `.env` files are used for configuration locally, sensitive credentials should be stored securely in managed services like Google Cloud Secret Manager in production deployments and accessed by the Cloud Run service account.
*   **CORS:** Flask-CORS is configured to control which origins are allowed to make requests to the API, preventing unauthorized cross-origin access.

## 📄 License

This project is licensed under the MIT License.
