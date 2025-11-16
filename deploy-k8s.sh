#!/bin/bash

# Deploy AI Coder to Kubernetes
# Usage: ./deploy-k8s.sh

set -e

echo "🚀 Deploying AI Coder to Kubernetes"
echo ""

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f kubernetes/namespace.yaml
echo "✅ Namespace created"

# Apply ConfigMap and Secrets
echo "⚙️  Applying ConfigMap..."
kubectl apply -f kubernetes/configmap.yaml
echo "✅ ConfigMap applied"

echo "🔐 Applying Secrets..."
kubectl apply -f kubernetes/secrets.yaml
echo "✅ Secrets applied"

# Deploy Redis
echo "🗄️  Deploying Redis..."
kubectl apply -f kubernetes/redis-deployment.yaml
echo "✅ Redis deployed"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
kubectl wait --for=condition=ready pod -l app=redis -n ai-coder --timeout=120s
echo "✅ Redis is ready"

# Deploy Backend API
echo "🔧 Deploying Backend API..."
kubectl apply -f kubernetes/backend-api-deployment.yaml
echo "✅ Backend API deployed"

# Deploy Agent Phases
echo "🤖 Deploying Phase 1 Agents (Discovery)..."
kubectl apply -f kubernetes/phase1-agent-deployment.yaml

echo "🤖 Deploying Phase 2 Agents (Design)..."
kubectl apply -f kubernetes/phase2-agent-deployment.yaml

echo "🤖 Deploying Phase 3 Agents (Implementation)..."
kubectl apply -f kubernetes/phase3-agent-deployment.yaml

echo "🤖 Deploying Phase 4 Agents (QA)..."
kubectl apply -f kubernetes/phase4-agent-deployment.yaml

echo "🤖 Deploying Phase 5 Agents (Validation)..."
kubectl apply -f kubernetes/phase5-agent-deployment.yaml

echo "🤖 Deploying Phase 6 Agents (Monitoring)..."
kubectl apply -f kubernetes/phase6-agent-deployment.yaml

echo "✅ All agent phases deployed"

# Deploy Frontend
echo "🌐 Deploying Frontend..."
kubectl apply -f kubernetes/frontend-deployment.yaml
echo "✅ Frontend deployed"

# Deploy Ingress
echo "🌍 Deploying Ingress..."
kubectl apply -f kubernetes/ingress.yaml
echo "✅ Ingress deployed"

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📊 Checking status..."
kubectl get pods -n ai-coder
echo ""
kubectl get svc -n ai-coder
echo ""
kubectl get hpa -n ai-coder
echo ""

echo "📋 Useful commands:"
echo "  • Watch pods: kubectl get pods -n ai-coder -w"
echo "  • View logs: kubectl logs -f -n ai-coder -l app=backend-api"
echo "  • Check HPA: kubectl get hpa -n ai-coder"
echo "  • Port forward API: kubectl port-forward -n ai-coder svc/backend-api-service 8000:8000"
echo "  • Port forward Frontend: kubectl port-forward -n ai-coder svc/frontend-service 3000:80"
echo ""
echo "🌐 Access your application:"
echo "  • API: http://localhost:8000 (after port-forward)"
echo "  • Frontend: http://localhost:3000 (after port-forward)"
echo "  • Or configure Ingress with your domain"

