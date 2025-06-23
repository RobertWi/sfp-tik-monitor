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
  uid   = "routeros-20250623"
}

resource "grafana_folder" "sfp_monitoring" {
  title = "SFP Monitoring Private"
  uid   = "sfp-20250623"
  parent_folder_uid = grafana_folder.routeros_monitoring.uid
}

resource "grafana_folder" "alerts" {
  title = "SFP Monitoring Alerts"
  uid   = "alerts-20250623"
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