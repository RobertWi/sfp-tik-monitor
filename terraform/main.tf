# Local values for consistent tagging
locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Component   = "monitoring"
  }
}

# Call modules
module "folders" {
  source = "./modules/folders"
  
  environment = var.environment
  project_name = var.project_name
  common_tags = local.common_tags
}

module "dashboards" {
  source = "./modules/dashboards"
  
  environment = var.environment
  project_name = var.project_name
  common_tags = local.common_tags
  folder_uid = module.folders.sfp_folder_uid
}

module "alerts" {
  source = "./modules/alerts"
  
  environment = var.environment
  project_name = var.project_name
  common_tags = local.common_tags
  
  # Pass alert-specific variables
  folder_uid = module.folders.alerts_folder_uid
  datasource_uid = var.datasource_uid
  alert_evaluation_interval = var.alert_evaluation_interval
  sfp_temperature_critical_threshold = var.sfp_temperature_critical_threshold
  sfp_rx_power_low_threshold = var.sfp_rx_power_low_threshold
  sfp_rx_power_high_threshold = var.sfp_rx_power_high_threshold
  ont_cpu_warning_threshold = var.ont_cpu_warning_threshold
  contact_point_name = var.contact_point_name
  notification_policy_name = var.notification_policy_name
  notification_group_by = var.notification_group_by
  notification_group_wait = var.notification_group_wait
  notification_group_interval = var.notification_group_interval
  notification_repeat_interval = var.notification_repeat_interval
  email_address = var.email_address
}

# Outputs
output "folder_urls" {
  description = "URLs of created folders"
  value       = module.folders.folder_urls
}

output "dashboard_urls" {
  description = "URLs of created dashboards"
  value       = module.dashboards.dashboard_urls
}

output "alert_rule_ids" {
  description = "IDs of created alert rules"
  value       = module.alerts.alert_rule_ids
}