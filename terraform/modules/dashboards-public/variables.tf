variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
}

variable "grafana_url" {
  description = "Grafana instance URL"
  type        = string
  default     = "doemijdiemetriekmaar.grafana.net"
} 