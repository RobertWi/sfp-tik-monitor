terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 3.25"
    }
  }
}

# SFP Monitoring Dashboard
resource "grafana_dashboard" "sfp_monitoring" {
  config_json = file("${path.module}/sfp-monitor-dashboard.json")
  folder      = var.folder_uid
}

# Variables for the module
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to resources"
  type        = map(string)
}

variable "folder_uid" {
  description = "UID of the folder to store the dashboard"
  type        = string
  default     = null
}

# Outputs
output "dashboard_urls" {
  description = "URLs of created dashboards"
  value = {
    sfp_monitoring = grafana_dashboard.sfp_monitoring.url
  }
} 