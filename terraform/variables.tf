# Grafana Cloud Configuration
variable "grafana_url" {
  description = "Grafana Cloud instance URL (e.g., https://your-instance.grafana.net)"
  type        = string
  validation {
    condition     = can(regex("^https://.*\\.grafana\\.net$", var.grafana_url))
    error_message = "Grafana URL must be a valid Grafana Cloud URL ending with .grafana.net"
  }
}

variable "grafana_auth" {
  description = "Grafana Cloud API key (service account token)"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.grafana_auth) > 0
    error_message = "Grafana auth token cannot be empty"
  }
}

variable "grafana_prometheus_url" {
  description = "The URL of the Grafana Cloud Prometheus datasource"
  type        = string
  default     = "https://prometheus-prod-25-eu-west-1.grafana.net"
}

# Environment Configuration
variable "environment" {
  description = "The deployment environment (e.g., 'production', 'staging')"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["production", "staging", "development", "testing"], var.environment)
    error_message = "Environment must be one of: production, staging, development, testing"
  }
}

variable "project_name" {
  description = "Project name for resource tagging and organization"
  type        = string
  default     = "sfp-monitoring"
  validation {
    condition     = length(var.project_name) >= 3 && length(var.project_name) <= 50
    error_message = "Project name must be between 3 and 50 characters"
  }
}

# Monitoring Configuration
variable "monitoring_interval" {
  description = "Default monitoring interval in seconds"
  type        = number
  default     = 30
  validation {
    condition     = var.monitoring_interval >= 10 && var.monitoring_interval <= 300
    error_message = "Monitoring interval must be between 10 and 300 seconds"
  }
}

variable "alert_evaluation_interval" {
  description = "Alert evaluation interval in seconds"
  type        = number
  default     = 90
  validation {
    condition     = var.alert_evaluation_interval >= 10 && var.alert_evaluation_interval <= 300
    error_message = "Alert evaluation interval must be between 10 and 300 seconds"
  }
}

# SFP Monitoring Thresholds
variable "sfp_rx_power_low_threshold" {
  description = "SFP RX power low threshold in dBm"
  type        = number
  default     = -30.0
  validation {
    condition     = var.sfp_rx_power_low_threshold >= -40.0 && var.sfp_rx_power_low_threshold <= -10.0
    error_message = "SFP RX power low threshold must be between -40.0 and -10.0 dBm"
  }
}

variable "sfp_rx_power_high_threshold" {
  description = "SFP RX power high threshold in dBm"
  type        = number
  default     = -8.0
  validation {
    condition     = var.sfp_rx_power_high_threshold >= -20.0 && var.sfp_rx_power_high_threshold <= 0.0
    error_message = "SFP RX power high threshold must be between -20.0 and 0.0 dBm"
  }
}

variable "sfp_temperature_warning_threshold" {
  description = "SFP temperature warning threshold in Celsius"
  type        = number
  default     = 70.0
  validation {
    condition     = var.sfp_temperature_warning_threshold >= 50.0 && var.sfp_temperature_warning_threshold <= 80.0
    error_message = "SFP temperature warning threshold must be between 50.0 and 80.0 Celsius"
  }
}

variable "sfp_temperature_critical_threshold" {
  description = "SFP temperature critical threshold in Celsius"
  type        = number
  default     = 85.0
  validation {
    condition     = var.sfp_temperature_critical_threshold >= 70.0 && var.sfp_temperature_critical_threshold <= 95.0
    error_message = "SFP temperature critical threshold must be between 70.0 and 95.0 Celsius"
  }
}

# ONT Monitoring Thresholds
variable "ont_cpu_warning_threshold" {
  description = "ONT CPU usage warning threshold in percent"
  type        = number
  default     = 80.0
  validation {
    condition     = var.ont_cpu_warning_threshold >= 50.0 && var.ont_cpu_warning_threshold <= 95.0
    error_message = "ONT CPU warning threshold must be between 50.0 and 95.0 percent"
  }
}

variable "ont_memory_warning_threshold" {
  description = "ONT memory usage warning threshold in percent"
  type        = number
  default     = 85.0
  validation {
    condition     = var.ont_memory_warning_threshold >= 60.0 && var.ont_memory_warning_threshold <= 95.0
    error_message = "ONT memory warning threshold must be between 60.0 and 95.0 percent"
  }
}

# Notification Configuration
variable "notification_policy_name" {
  description = "Name for the notification policy"
  type        = string
  default     = "SFP Monitoring Alerts"
}

variable "contact_point_name" {
  description = "Name for the contact point"
  type        = string
  default     = "SFP Monitoring Team"
}

variable "notification_group_by" {
  description = "Fields to group notifications by"
  type        = list(string)
  default     = ["alertname", "interface_name", "severity"]
}

variable "notification_group_wait" {
  description = "Time to wait before sending initial notification"
  type        = string
  default     = "30s"
}

variable "notification_group_interval" {
  description = "Time to wait before sending subsequent notifications"
  type        = string
  default     = "5m"
}

variable "notification_repeat_interval" {
  description = "Time to wait before repeating notifications"
  type        = string
  default     = "4h"
}

variable "email_address" {
  description = "Email address for alert notifications"
  type        = string
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.email_address))
    error_message = "Email address must be a valid email format"
  }
}

variable "datasource_uid" {
  description = "UID of the Prometheus datasource in Grafana Cloud. Find this in the Grafana UI under Connections > Data sources."
  type        = string
} 