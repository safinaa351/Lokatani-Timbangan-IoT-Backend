#!/bin/bash

# Configuration - using your specific values
PROJECT_ID="pk-lokatani"
SERVICE_NAME="flask-backend"
REGION="asia-southeast2"
REPO_NAME="flask-backend-repo"
IMAGE_NAME="vegetable-iot-backend"
FULL_IMAGE_PATH="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:latest"

echo "🚀 Starting deployment process for $SERVICE_NAME..."

# Build the Docker image locally
echo "🔨 Building Docker image..."
docker build -t $IMAGE_NAME:latest .

# Tag the image for Artifact Registry
echo "🏷️ Tagging image for Artifact Registry..."
docker tag $IMAGE_NAME:latest $FULL_IMAGE_PATH

# Push the image to Artifact Registry
echo "⬆️ Pushing image to Artifact Registry..."
docker push $FULL_IMAGE_PATH

# Deploy to Cloud Run
echo "🚢 Deploying to Cloud Run in $REGION..."
gcloud run deploy $SERVICE_NAME \
  --image $FULL_IMAGE_PATH \
  --region $REGION

echo "✅ Deployment complete!"