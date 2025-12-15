# Variables
IMAGE_NAME = codeinterpreter-wrapper
TAG = latest
K8S_FILE = k8s-deployment.yaml
NAMESPACE = default

.PHONY: all build push deploy clean

# Default target
all: build

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME):$(TAG) .

# Push the Docker image (Optional - requires registry configuration)
# Usage: make push IMAGE_NAME=myregistry/codeinterpreter-wrapper
push:
	docker push $(IMAGE_NAME):$(TAG)

# Deploy to Kubernetes
# Usage: make deploy [NAMESPACE=custom-namespace]
deploy:
	kubectl apply -f $(K8S_FILE) -n $(NAMESPACE)

# Delete deployment from Kubernetes
undeploy:
	kubectl delete -f $(K8S_FILE) -n $(NAMESPACE) --ignore-not-found=true

# Clean up local docker images
clean:
	docker rmi $(IMAGE_NAME):$(TAG)
