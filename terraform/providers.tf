terraform {
  required_version = ">= 1.0"
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 3.25"
    }
  }
}

# Configure Grafana Cloud provider
provider "grafana" {
  url  = var.grafana_url
  auth = var.grafana_auth
} 