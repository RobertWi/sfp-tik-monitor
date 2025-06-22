terraform {
  required_providers {
    grafana = {
      source  = "grafana/grafana"
      version = "~> 3.25"
    }
  }
}

# Notification Policy
resource "grafana_notification_policy" "sfp_monitoring" {
  contact_point = var.contact_point_name

  group_by = var.notification_group_by

  group_wait      = var.notification_group_wait
  group_interval  = var.notification_group_interval
  repeat_interval = var.notification_repeat_interval
}

# Variables
variable "contact_point_name" {
  description = "Name of the contact point to use"
  type        = string
}

variable "notification_group_by" {
  description = "Labels to group notifications by"
  type        = list(string)
  default     = ["alertname", "severity"]
}

variable "notification_group_wait" {
  description = "Time to wait before sending initial notification"
  type        = string
  default     = "30s"
}

variable "notification_group_interval" {
  description = "Time to wait before sending a new notification when a group of alerts changes"
  type        = string
  default     = "5m"
}

variable "notification_repeat_interval" {
  description = "Time to wait before repeating a notification"
  type        = string
  default     = "4h"
}

# Outputs
output "notification_policy_name" {
  description = "Name of the created notification policy"
  value       = grafana_notification_policy.sfp_monitoring.id
} 