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

# Cleanup function
cleanup_old_files() {
    print_status "Cleaning up old state and plan files..."
    # Remove old state backups but keep the latest
    find . -name "terraform.tfstate.[0-9]*.backup" -delete
    # Remove old plan files
    rm -f tfplan
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

# Clean up old files first
cleanup_old_files

# Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Validate configuration
print_status "Validating Terraform configuration..."
terraform validate

# Show and save plan
print_status "Creating deployment plan..."
terraform plan -out=tfplan

# Ask for confirmation
echo
read -p "Do you want to apply this configuration? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Applying Terraform configuration..."
    terraform apply tfplan
    print_status "Deployment completed successfully!"
    
    # Show outputs
    echo
    print_status "Deployment outputs:"
    terraform output

    # Clean up plan file after successful apply
    print_status "Cleaning up plan file..."
    rm -f tfplan
else
    print_warning "Deployment cancelled by user."
    print_status "Cleaning up plan file..."
    rm -f tfplan
    exit 0
fi 