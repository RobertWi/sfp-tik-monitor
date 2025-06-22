#!/bin/bash

# Terraform destroy script for SFP Monitoring Infrastructure
# This script helps destroy the monitoring infrastructure

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

print_status "Starting Terraform destroy process..."

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    print_error "terraform.tfvars file not found!"
    print_status "Please copy terraform.tfvars.example to terraform.tfvars and update the values."
    exit 1
fi

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    print_status "Initializing Terraform..."
    terraform init
fi

# Show what will be destroyed
print_status "Showing what will be destroyed..."
terraform plan -destroy

# Ask for confirmation
echo
print_warning "This will destroy ALL resources created by Terraform!"
read -p "Are you sure you want to destroy the infrastructure? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Destroying Terraform infrastructure..."
    terraform destroy -auto-approve
    print_status "Infrastructure destroyed successfully!"
else
    print_warning "Destroy cancelled by user."
    exit 0
fi 