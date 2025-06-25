// Public read-only dashboard
resource "grafana_dashboard" "sfp_monitoring_public" {
  config_json = file("${path.module}/sfp-monitor-dashboard.json")
  folder      = var.folder_uid
}

resource "grafana_dashboard_public" "sfp_monitoring_public" {
  dashboard_uid = grafana_dashboard.sfp_monitoring_public.uid
  
  time_selection_enabled = true
  annotations_enabled    = true
  is_enabled            = true
}

variable "folder_uid" {
  description = "The UID of the folder to place the dashboard in"
  type        = string
}

output "dashboard_urls" {
  description = "URLs of created dashboards"
  value = {
    sfp_monitoring_public = "https://${var.grafana_url}/d/${grafana_dashboard.sfp_monitoring_public.uid}/sfp-monitor-dashboard-public"
  }
}

output "public_dashboard_urls" {
  description = "Public dashboard URLs for anonymous access"
  value = {
    sfp_monitoring_public = "https://${var.grafana_url}/public-dashboards/${grafana_dashboard_public.sfp_monitoring_public.uid}"
  }
} 