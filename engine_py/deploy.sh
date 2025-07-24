#!/bin/bash

# Deploy President Game Backend
echo "🚀 Deploying President Game Backend..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t president-engine:latest .

# Tag for registry (replace with your registry)
# docker tag president-engine:latest your-registry/president-engine:latest

# Push to registry (uncomment if using remote registry)
# docker push your-registry/president-engine:latest

echo "✅ Build complete!"
echo ""
echo "📋 Deployment options:"
echo "1. Deploy to Koyeb:"
echo "   koyeb app init president-game-backend --docker president-engine:latest --ports 8000:http --routes /:8000"
echo ""
echo "2. Deploy to Railway:"
echo "   railway login && railway init && railway up"
echo ""
echo "3. Deploy to Render:"
echo "   Create a new Web Service and point to this Dockerfile"
echo ""
echo "4. Run locally:"
echo "   docker run -p 8000:8000 president-engine:latest" 