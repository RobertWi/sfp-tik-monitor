terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 3.25"
    }
  }
}

# Grafana Folders for organizing dashboards and alert rules
resource "grafana_folder" "routeros_monitoring" {
  title = "RouterOS Monitoring"
  uid   = "routeros"
}

resource "grafana_folder" "sfp_monitoring" {
  title = "SFP Monitoring"
  uid   = "sfp"
  parent_folder_uid = grafana_folder.routeros_monitoring.uid
}

resource "grafana_folder" "alerts" {
  title = "Alerts"
  uid   = "alerts"
  parent_folder_uid = grafana_folder.routeros_monitoring.uid
}

# Variables
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

# Outputs
output "routeros_folder_uid" {
  description = "UID of the RouterOS Monitoring folder"
  value       = grafana_folder.routeros_monitoring.uid
}

output "sfp_folder_uid" {
  description = "UID of the SFP Monitoring folder"
  value       = grafana_folder.sfp_monitoring.uid
}

output "alerts_folder_uid" {
  description = "UID of the Alerts folder"
  value       = grafana_folder.alerts.uid
}

output "folder_urls" {
  description = "URLs of created folders"
  value = {
    routeros = grafana_folder.routeros_monitoring.url
    sfp      = grafana_folder.sfp_monitoring.url
    alerts   = grafana_folder.alerts.url
  }
} 