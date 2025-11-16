#!/bin/bash

# Build and push all Docker images for Kubernetes deployment
# Usage: ./build-images.sh [registry-url]

set -e

# Default registry (change this to your registry)
REGISTRY=${1:-"localhost:5000/ai-coder"}

echo "🐳 Building AI Coder Docker Images"
echo "Registry: $REGISTRY"
echo ""

# Build Backend API
echo "📦 Building Backend API..."
docker build -f Dockerfile.backend -t $REGISTRY/backend:latest .
echo "✅ Backend API built"

# Build Phase 1 Agent
echo "📦 Building Phase 1 Agent (Discovery)..."
docker build -f Dockerfile.phase1-agent -t $REGISTRY/phase1-agent:latest .
echo "✅ Phase 1 Agent built"

# Build Phase 2 Agent
echo "📦 Building Phase 2 Agent (Design)..."
docker build -f Dockerfile.phase2-agent -t $REGISTRY/phase2-agent:latest .
echo "✅ Phase 2 Agent built"

# Build Phase 3 Agent
echo "📦 Building Phase 3 Agent (Implementation)..."
docker build -f Dockerfile.phase3-agent -t $REGISTRY/phase3-agent:latest .
echo "✅ Phase 3 Agent built"

# Build Phase 4 Agent
echo "📦 Building Phase 4 Agent (QA)..."
docker build -f Dockerfile.phase4-agent -t $REGISTRY/phase4-agent:latest .
echo "✅ Phase 4 Agent built"

# Build Phase 5 Agent
echo "📦 Building Phase 5 Agent (Validation)..."
docker build -f Dockerfile.phase5-agent -t $REGISTRY/phase5-agent:latest .
echo "✅ Phase 5 Agent built"

# Build Phase 6 Agent
echo "📦 Building Phase 6 Agent (Monitoring)..."
docker build -f Dockerfile.phase6-agent -t $REGISTRY/phase6-agent:latest .
echo "✅ Phase 6 Agent built"

# Build Frontend
echo "📦 Building Frontend..."
docker build -f Dockerfile.frontend -t $REGISTRY/frontend:latest .
echo "✅ Frontend built"

echo ""
echo "🎉 All images built successfully!"
echo ""

# Ask to push
read -p "Push images to registry? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "🚀 Pushing images to $REGISTRY..."
    
    docker push $REGISTRY/backend:latest
    docker push $REGISTRY/phase1-agent:latest
    docker push $REGISTRY/phase2-agent:latest
    docker push $REGISTRY/phase3-agent:latest
    docker push $REGISTRY/phase4-agent:latest
    docker push $REGISTRY/phase5-agent:latest
    docker push $REGISTRY/phase6-agent:latest
    docker push $REGISTRY/frontend:latest
    
    echo "✅ All images pushed!"
else
    echo "⏭️  Skipping push"
fi

echo ""
echo "📋 Next steps:"
echo "1. Update kubernetes/*.yaml files with your registry URL"
echo "2. Configure secrets: kubectl apply -f kubernetes/secrets.yaml"
echo "3. Deploy: ./deploy-k8s.sh"

