resource "grafana_dashboard" "sfp_monitoring_public" {
  config_json = file("${path.module}/sfp-monitor-dashboard-public.json")
  folder      = grafana_folder.sfp_monitoring.id
}

resource "grafana_dashboard_public" "sfp_monitoring_public" {
  dashboard_uid = grafana_dashboard.sfp_monitoring_public.uid
  
  time_selection_enabled = true
  annotations_enabled    = true
  is_enabled            = true
}

resource "grafana_folder" "sfp_monitoring" {
  title = "SFP Monitoring"
}

output "dashboard_urls" {
  description = "URLs of created public dashboards"
  value = {
    sfp_monitoring_public = "https://${var.grafana_url}/d/${grafana_dashboard.sfp_monitoring_public.uid}/sfp-monitor-dashboard-public"
  }
}

output "public_dashboard_urls" {
  description = "Public dashboard URLs for anonymous access"
  value = {
    sfp_monitoring_public = "https://${var.grafana_url}/public-dashboards/${grafana_dashboard.sfp_monitoring_public.uid}"
  }
} 