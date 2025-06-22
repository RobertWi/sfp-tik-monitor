# Call submodules
module "contact_points" {
  source = "./submodules/contact-points"
  
  contact_point_name = var.contact_point_name
  email_address = var.email_address
}

module "notification_policies" {
  source = "./submodules/notification-policies"
  
  contact_point_name = module.contact_points.contact_point_name
  notification_group_by = var.notification_group_by
  notification_group_wait = var.notification_group_wait
  notification_group_interval = var.notification_group_interval
  notification_repeat_interval = var.notification_repeat_interval
}

module "alert_rules" {
  source = "./submodules/alert-rules"
  
  folder_uid = var.folder_uid
  datasource_uid = var.datasource_uid
  alert_evaluation_interval = var.alert_evaluation_interval
  sfp_temperature_critical_threshold = var.sfp_temperature_critical_threshold
  sfp_rx_power_low_threshold = var.sfp_rx_power_low_threshold
  sfp_rx_power_high_threshold = var.sfp_rx_power_high_threshold
  ont_cpu_warning_threshold = var.ont_cpu_warning_threshold
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

variable "alert_evaluation_interval" {
  description = "Alert evaluation interval in seconds"
  type        = number
  default     = 60
}

variable "sfp_temperature_critical_threshold" {
  description = "Critical temperature threshold for SFP modules (°C)"
  type        = number
  default     = 70
}

variable "sfp_rx_power_low_threshold" {
  description = "Low RX power threshold for SFP modules (dBm)"
  type        = number
  default     = -25
}

variable "sfp_rx_power_high_threshold" {
  description = "High RX power threshold for SFP modules (dBm)"
  type        = number
  default     = -3
}

variable "ont_cpu_warning_threshold" {
  description = "Warning threshold for ONT CPU usage (%)"
  type        = number
  default     = 80
}

variable "contact_point_name" {
  description = "Name for the contact point"
  type        = string
  default     = "sfp-monitoring-contact-point"
}

variable "notification_policy_name" {
  description = "Name for the notification policy"
  type        = string
  default     = "sfp-monitoring-notification-policy"
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

variable "email_address" {
  description = "Email address for notifications"
  type        = string
}

variable "folder_uid" {
  description = "UID of the folder to store alert rules. Set to null to use General folder."
  type        = string
  default     = null
}

variable "datasource_uid" {
  description = "UID of the Grafana datasource to use for alerts."
  type        = string
}

# Outputs
output "alert_rule_ids" {
  description = "IDs of created alert rules"
  value       = module.alert_rules.alert_rule_ids
}

output "contact_point_name" {
  description = "Name of the created contact point"
  value       = module.contact_points.contact_point_name
}

output "notification_policy_name" {
  description = "Name of the created notification policy"
  value       = module.notification_policies.notification_policy_name
} 