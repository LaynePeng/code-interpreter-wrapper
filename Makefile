# Docker & K8s Configuration
# Set your registry (e.g., docker.io/yourusername or your-private-registry.com)
REGISTRY ?= layne-docker-registry
IMAGE_NAME ?= codeinterpreter-wrapper
TAG ?= latest

# Combine to full image name
FULL_IMAGE := $(REGISTRY)/$(IMAGE_NAME):$(TAG)

# Kubernetes Configuration
NAMESPACE ?= default
K8S_FILE := k8s/deployment.yaml

.PHONY: all build push deploy clean

all: build push deploy

# 1. Build Docker Image
build:
	@echo "Building Docker image: $(FULL_IMAGE)..."
	docker build -t $(FULL_IMAGE) .

# 2. Push Docker Image to Registry
push:
	@echo "Pushing Docker image: $(FULL_IMAGE)..."
	docker push $(FULL_IMAGE)

# 3. Apply to Kubernetes
# Uses sed to replace the placeholder in the yaml file with the actual image name, then pipes to kubectl
deploy:
	@echo "Deploying to Kubernetes (Namespace: $(NAMESPACE))..."
	@sed 's|IMAGE_PLACEHOLDER|$(FULL_IMAGE)|g' $(K8S_FILE) | kubectl apply -n $(NAMESPACE) -f -
	@echo "Deployment applied."

# Utility: Delete from Kubernetes
undeploy:
	@echo "Deleting deployment from Kubernetes..."
	kubectl delete -f $(K8S_FILE) -n $(NAMESPACE)

# Utility: Show logs
logs:
	@echo "Fetching logs..."
	kubectl logs -l app=$(IMAGE_NAME) -n $(NAMESPACE) -f
