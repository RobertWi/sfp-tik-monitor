#!/bin/bash

# Terraform deployment script for SFP Monitoring Infrastructure
# This script helps deploy the monitoring infrastructure to Grafana Cloud

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    print_error "terraform.tfvars file not found!"
    print_status "Please copy terraform.tfvars.example to terraform.tfvars and update the values."
    exit 1
fi

# Check if required variables are set
if ! grep -q "grafana_url" terraform.tfvars || ! grep -q "grafana_auth" terraform.tfvars; then
    print_error "Required variables grafana_url and grafana_auth must be set in terraform.tfvars"
    exit 1
fi

print_status "Starting Terraform deployment..."

# Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Validate configuration
print_status "Validating Terraform configuration..."
terraform validate

# Show plan
print_status "Showing deployment plan..."
terraform plan

# Ask for confirmation
echo
read -p "Do you want to apply this configuration? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Applying Terraform configuration..."
    terraform apply -auto-approve
    print_status "Deployment completed successfully!"
    
    # Show outputs
    echo
    print_status "Deployment outputs:"
    terraform output
else
    print_warning "Deployment cancelled by user."
    exit 0
fi 