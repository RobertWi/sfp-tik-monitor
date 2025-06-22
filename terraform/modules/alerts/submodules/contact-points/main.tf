terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 3.25"
    }
  }
}

# Contact Point for notifications
resource "grafana_contact_point" "sfp_monitoring" {
  name = var.contact_point_name

  email {
    addresses = [var.email_address]
    subject   = "SFP Monitoring Alert: {{ .GroupLabels.alertname }}"
    message   = "Alert: {{ .GroupLabels.alertname }}\nSeverity: {{ .GroupLabels.severity }}\nInterface: {{ .GroupLabels.interface_name }}\nValue: {{ .CommonAnnotations.summary }}\n\n{{ .CommonAnnotations.description }}"
  }

  # Add more notification channels as needed
  # slack {
  #   url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
  #   title = "SFP Monitoring Alert"
  #   text = "Alert: {{ .GroupLabels.alertname }}\nSeverity: {{ .GroupLabels.severity }}\nInterface: {{ .GroupLabels.interface_name }}"
  # }
}

# Variables
variable "contact_point_name" {
  description = "Name for the contact point"
  type        = string
}

variable "email_address" {
  description = "Email address for notifications"
  type        = string
}

# Outputs
output "contact_point_name" {
  description = "Name of the created contact point"
  value       = grafana_contact_point.sfp_monitoring.name
} 